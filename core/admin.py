from django.contrib import admin
from .models import AccountProfile, AuditEvent, PaymentMethod, PlatformSetting, TradeSignal, PaymentRequest


@admin.register(AccountProfile)
class AccountProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'can_login', 'can_trade', 'can_withdraw', 'kyc_required', 'updated_at')
    list_filter = ('status', 'can_login', 'can_trade', 'can_withdraw', 'kyc_required')
    search_fields = ('user__username', 'user__email', 'restriction_reason')
    readonly_fields = ('created_at', 'updated_at', 'updated_by')
    fieldsets = (
        ('Account', {'fields': ('user', 'status')}),
        ('Permissions', {'fields': ('can_login', 'can_trade', 'can_withdraw', 'kyc_required')}),
        ('Restriction details', {'fields': ('restriction_reason',)}),
        ('Audit', {'fields': ('created_at', 'updated_at', 'updated_by')}),
    )
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('action', 'object_type', 'object_id', 'actor', 'created_at')
    list_filter = ('action', 'object_type')
    search_fields = ('object_id', 'action', 'object_type')
    readonly_fields = ('actor', 'action', 'object_type', 'object_id', 'details', 'created_at')
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


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
