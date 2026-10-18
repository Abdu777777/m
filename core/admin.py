from django.contrib import admin
from django.utils import timezone
from .models import AccountProfile, AuditEvent, KYCSubmission, LedgerAccount, LedgerEntry, LedgerTransaction, MoneyRequest, PaymentMethod, PlatformSetting, TradeSignal, PaymentRequest


@admin.register(AccountProfile)
class AccountProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'can_login', 'can_trade', 'can_withdraw', 'kyc_required', 'updated_at')
    list_filter = ('status', 'can_login', 'can_trade', 'can_withdraw', 'kyc_required')
    search_fields = ('user__username', 'user__email', 'restriction_reason')
    readonly_fields = ('created_at', 'updated_at', 'updated_by')
    fieldsets = (('Account', {'fields': ('user', 'status')}), ('Permissions', {'fields': ('can_login', 'can_trade', 'can_withdraw', 'kyc_required')}), ('Restriction details', {'fields': ('restriction_reason',)}), ('Audit', {'fields': ('created_at', 'updated_at', 'updated_by')}))
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(MoneyRequest)
class MoneyRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'kind', 'amount', 'currency', 'payment_method', 'status', 'created_at', 'reviewed_by')
    list_filter = ('kind', 'status', 'currency', 'payment_method')
    search_fields = ('user__username', 'user__email', 'transaction_reference')
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at', 'reviewed_by')
    def save_model(self, request, obj, form, change):
        if obj.status != 'pending':
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


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


@admin.register(PlatformSetting)
class PlatformSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'description', 'updated_by', 'updated_at')
    search_fields = ('key', 'description')
    readonly_fields = ('updated_at',)


@admin.register(TradeSignal)
class TradeSignalAdmin(admin.ModelAdmin):
    list_display = ('symbol','market','direction','entry','stop_loss','target_1','status','result_r','is_published','published_at')
    list_filter = ('market','direction','status','is_published')
    search_fields = ('symbol','title','analysis','source_name')
    list_editable = ('status','is_published')
    readonly_fields = ('created_at','updated_at')


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('full_name','email','plan','method','status','created_at')
    list_filter = ('plan','method','status')
    search_fields = ('full_name','email','transaction_reference')
    list_editable = ('status',)
    readonly_fields = ('created_at',)


@admin.register(KYCSubmission)
class KYCSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'status', 'created_at', 'reviewed_by', 'reviewed_at')
    list_filter = ('status', 'document_type')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user', 'document_type', 'document_file', 'applicant_note', 'created_at', 'updated_at', 'reviewed_by', 'reviewed_at')
    fields = ('user', 'document_type', 'document_file', 'applicant_note', 'status', 'reviewer_note', 'created_at', 'updated_at', 'reviewed_by', 'reviewed_at')
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.has_perm('core.review_kycsubmission')
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def save_model(self, request, obj, form, change):
        if obj.status in ('approved', 'rejected'):
            obj.reviewed_by = request.user
            from django.utils import timezone
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)
