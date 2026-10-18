from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.db import transaction
from django.utils import timezone
from .finance import MoneyRequestWorkflowError, settle_money_request
from .models import AccountProfile, AuditEvent, KYCSubmission, LedgerAccount, LedgerEntry, LedgerTransaction, MoneyRequest, PaymentMethod, PlatformSetting, TradeSignal, PaymentRequest


def record_admin_audit(request, obj, action, form=None, previous_status=None):
    changed_fields = list(form.changed_data) if form is not None else []
    details = {'changed_fields': changed_fields}
    if previous_status is not None:
        state_field = previous_status['field']
        details['previous_state'] = previous_status['value']
        details['new_state'] = getattr(obj, state_field, None)
    AuditEvent.objects.create(
        actor=request.user,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(obj.pk or ''),
        details=details,
    )


def get_previous_status(obj, change):
    if not change or not obj.pk:
        return None
    field_names = {field.name for field in obj._meta.fields}
    state_field = 'status' if 'status' in field_names else 'is_active' if 'is_active' in field_names else None
    if state_field is None:
        return None
    value = obj.__class__.objects.filter(pk=obj.pk).values_list(state_field, flat=True).first()
    return {'field': state_field, 'value': value}


@admin.register(AccountProfile)
class AccountProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'can_login', 'can_trade', 'can_withdraw', 'kyc_required', 'updated_at')
    list_filter = ('status', 'can_login', 'can_trade', 'can_withdraw', 'kyc_required')
    search_fields = ('user__username', 'user__email', 'restriction_reason')
    readonly_fields = ('created_at', 'updated_at', 'updated_by')
    fieldsets = (('Account', {'fields': ('user', 'status')}), ('Permissions', {'fields': ('can_login', 'can_trade', 'can_withdraw', 'kyc_required')}), ('Restriction details', {'fields': ('restriction_reason',)}), ('Audit', {'fields': ('created_at', 'updated_at', 'updated_by')}))
    def save_model(self, request, obj, form, change):
        previous_status = get_previous_status(obj, change)
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        record_admin_audit(request, obj, 'admin_update', form, previous_status)



class SettlementEvidenceForm(forms.Form):
    evidence_reference = forms.CharField(
        max_length=180,
        label='External transaction reference',
        help_text='Enter the reference from the payment provider or transfer receipt.',
    )
    confirm_external_settlement = forms.BooleanField(
        required=True,
        label='I verified the external transfer independently.',
    )


@admin.register(MoneyRequest)
class MoneyRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'kind', 'amount', 'currency', 'payment_method', 'status', 'created_at', 'reviewed_by', 'settlement_link')
    list_filter = ('kind', 'status', 'currency', 'payment_method')
    search_fields = ('user__username', 'user__email', 'transaction_reference')
    readonly_fields = ('status', 'created_at', 'updated_at', 'reviewed_at', 'reviewed_by')
    actions = ('mark_selected_for_review', 'approve_selected_withdrawals', 'reject_selected_requests')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        custom_urls = [
            path('<path:object_id>/settle/', self.admin_site.admin_view(self.settle_view), name='core_moneyrequest_settle'),
        ]
        return custom_urls + super().get_urls()

    @admin.display(description='Manual settlement')
    def settlement_link(self, obj):
        if obj.kind == MoneyRequest.Kind.DEPOSIT and obj.status == MoneyRequest.Status.REVIEW:
            label = 'Verify deposit'
        elif obj.kind == MoneyRequest.Kind.WITHDRAWAL and obj.status == MoneyRequest.Status.APPROVED:
            label = 'Record withdrawal'
        else:
            return '—'
        url = reverse('admin:core_moneyrequest_settle', args=(obj.pk,))
        return format_html('<a href="{}">{}</a>', url, label)

    def settle_view(self, request, object_id):
        obj = get_object_or_404(MoneyRequest, pk=object_id)
        if not self.has_change_permission(request, obj):
            raise PermissionDenied
        if request.method == 'POST':
            form = SettlementEvidenceForm(request.POST)
            if form.is_valid():
                try:
                    settle_money_request(
                        request_id=obj.pk,
                        actor=request.user,
                        evidence_reference=form.cleaned_data['evidence_reference'],
                        confirm_received=(
                            obj.kind == MoneyRequest.Kind.DEPOSIT
                            and form.cleaned_data['confirm_external_settlement']
                        ),
                        confirm_sent=(
                            obj.kind == MoneyRequest.Kind.WITHDRAWAL
                            and form.cleaned_data['confirm_external_settlement']
                        ),
                    )
                except MoneyRequestWorkflowError as exc:
                    form.add_error(None, str(exc))
                else:
                    self.message_user(request, 'Settlement recorded in the internal ledger. No transfer was initiated by the platform.', messages.SUCCESS)
                    return redirect(reverse('admin:core_moneyrequest_change', args=(obj.pk,)))
        else:
            form = SettlementEvidenceForm()
        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'original': obj,
            'title': 'Record verified external settlement',
            'form': form,
            'back_url': reverse('admin:core_moneyrequest_change', args=(obj.pk,)),
        }
        return render(request, 'admin/core/moneyrequest/settle.html', context)

    @admin.action(description='Move eligible requests to under review')
    @transaction.atomic
    def mark_selected_for_review(self, request, queryset):
        changed = 0
        for obj in queryset.select_for_update().filter(status=MoneyRequest.Status.PENDING):
            previous = obj.status
            obj.status = MoneyRequest.Status.REVIEW
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
            obj.save(update_fields=('status', 'reviewed_by', 'reviewed_at', 'updated_at'))
            AuditEvent.objects.create(
                actor=request.user, action='money_request_review',
                object_type='MoneyRequest', object_id=str(obj.pk),
                details={'previous_state': previous, 'new_state': obj.status, 'kind': obj.kind, 'amount': str(obj.amount), 'currency': obj.currency},
            )
            changed += 1
        self.message_user(request, f'{changed} request(s) moved to review. No funds were moved.')

    @admin.action(description='Approve reviewed withdrawal requests (does not send funds)')
    @transaction.atomic
    def approve_selected_withdrawals(self, request, queryset):
        changed = 0
        eligible = queryset.filter(kind=MoneyRequest.Kind.WITHDRAWAL, status=MoneyRequest.Status.REVIEW)
        for obj in eligible.select_for_update():
            previous = obj.status
            obj.status = MoneyRequest.Status.APPROVED
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
            obj.save(update_fields=('status', 'reviewed_by', 'reviewed_at', 'updated_at'))
            AuditEvent.objects.create(
                actor=request.user, action='money_withdrawal_approved',
                object_type='MoneyRequest', object_id=str(obj.pk),
                details={'previous_state': previous, 'new_state': obj.status, 'kind': obj.kind, 'amount': str(obj.amount), 'currency': obj.currency},
            )
            changed += 1
        self.message_user(request, f'{changed} withdrawal request(s) approved. No funds were sent.')

    @admin.action(description='Reject pending or under-review requests')
    @transaction.atomic
    def reject_selected_requests(self, request, queryset):
        changed = 0
        eligible = queryset.filter(status__in=(MoneyRequest.Status.PENDING, MoneyRequest.Status.REVIEW))
        for obj in eligible.select_for_update():
            previous = obj.status
            obj.status = MoneyRequest.Status.REJECTED
            obj.admin_note = obj.admin_note or 'Rejected by administrator.'
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
            obj.save(update_fields=('status', 'admin_note', 'reviewed_by', 'reviewed_at', 'updated_at'))
            AuditEvent.objects.create(
                actor=request.user, action='money_request_rejected',
                object_type='MoneyRequest', object_id=str(obj.pk),
                details={'previous_state': previous, 'new_state': obj.status, 'kind': obj.kind, 'amount': str(obj.amount), 'currency': obj.currency},
            )
            changed += 1
        self.message_user(request, f'{changed} request(s) rejected. No funds were moved.')

    def save_model(self, request, obj, form, change):
        previous_status = get_previous_status(obj, change)
        if change:
            original = MoneyRequest.objects.get(pk=obj.pk)
            obj.status = original.status
            obj.reviewed_by = original.reviewed_by
            obj.reviewed_at = original.reviewed_at
        super().save_model(request, obj, form, change)
        record_admin_audit(request, obj, 'money_request_details_update', form, previous_status)


@admin.register(LedgerAccount)
class LedgerAccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'kind', 'owner', 'currency', 'is_active')
    list_filter = ('kind', 'currency', 'is_active')
    search_fields = ('code', 'owner__username')
    readonly_fields = ('created_at',)


@admin.register(LedgerTransaction)
class LedgerTransactionAdmin(admin.ModelAdmin):
    list_display = ('idempotency_key', 'description', 'status', 'created_by', 'created_at')
    search_fields = ('idempotency_key', 'description')
    readonly_fields = ('idempotency_key', 'description', 'status', 'created_by', 'created_at')
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'account', 'side', 'amount', 'currency', 'created_at')
    list_filter = ('side', 'currency')
    readonly_fields = ('transaction', 'account', 'side', 'amount', 'currency', 'created_at')
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('action', 'object_type', 'object_id', 'actor', 'created_at')
    list_filter = ('action', 'object_type')
    search_fields = ('object_id', 'action', 'object_type')
    readonly_fields = ('actor', 'action', 'object_type', 'object_id', 'details', 'created_at')
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'currency', 'accepts_deposits', 'accepts_withdrawals', 'is_active')
    list_filter = ('kind', 'currency', 'is_active')
    search_fields = ('name', 'network')
    readonly_fields = ('created_at', 'updated_at')
    def save_model(self, request, obj, form, change):
        previous_status = get_previous_status(obj, change)
        super().save_model(request, obj, form, change)
        record_admin_audit(request, obj, 'payment_method_update', form, previous_status)


@admin.register(PlatformSetting)
class PlatformSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'description', 'updated_by', 'updated_at')
    search_fields = ('key', 'description')
    readonly_fields = ('updated_at',)


@admin.register(TradeSignal)
class TradeSignalAdmin(admin.ModelAdmin):
    list_display = ('symbol','market','direction','entry','stop_loss','target_1','status','review_status','result_r','is_published','published_at')
    list_filter = ('market','direction','status','review_status','is_published')
    search_fields = ('symbol','title','analysis','source_name')
    list_editable = ('status','review_status','is_published')
    readonly_fields = ('created_at','updated_at')


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('full_name','email','plan','method','status','created_at')
    list_filter = ('plan','method','status')
    search_fields = ('full_name','email','transaction_reference')
    list_editable = ('status',)
    readonly_fields = ('created_at',)
    def save_model(self, request, obj, form, change):
        previous_status = get_previous_status(obj, change)
        super().save_model(request, obj, form, change)
        record_admin_audit(request, obj, 'subscription_payment_review', form, previous_status)


@admin.register(KYCSubmission)
class KYCSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'status', 'created_at', 'reviewed_by', 'reviewed_at')
    list_filter = ('status', 'document_type')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user', 'document_type', 'document_file', 'applicant_note', 'created_at', 'updated_at', 'reviewed_by', 'reviewed_at')
    fields = ('user', 'document_type', 'document_file', 'applicant_note', 'status', 'reviewer_note', 'created_at', 'updated_at', 'reviewed_by', 'reviewed_at')
    def _can_review_kyc(self, request):
        return request.user.is_superuser or request.user.has_perm('core.review_kycsubmission')
    def has_view_permission(self, request, obj=None):
        return self._can_review_kyc(request)
    def has_change_permission(self, request, obj=None):
        return self._can_review_kyc(request)
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def save_model(self, request, obj, form, change):
        previous_status = get_previous_status(obj, change)
        if obj.status in ('approved', 'rejected'):
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)
        record_admin_audit(request, obj, 'kyc_review', form, previous_status)
