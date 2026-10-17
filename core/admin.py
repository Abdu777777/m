from django.contrib import admin
from .models import TradeSignal, PaymentRequest

@admin.register(TradeSignal)
class TradeSignalAdmin(admin.ModelAdmin):
    list_display = ('symbol','market','direction','entry','stop_loss','target_1','status','result_r','is_published','published_at')
    list_filter = ('market','direction','status','is_published')
    search_fields = ('symbol','title','analysis')
    list_editable = ('status','is_published')
    readonly_fields = ('created_at','updated_at')

@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('full_name','email','plan','method','status','created_at')
    list_filter = ('plan','method','status')
    search_fields = ('full_name','email','transaction_reference')
    list_editable = ('status',)
    readonly_fields = ('created_at',)
