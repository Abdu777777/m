from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from .models import TradeSignal, PaymentRequest, PaymentMethod


def home(request):
    signals = TradeSignal.objects.filter(is_published=True).order_by('-published_at','-created_at')[:6]
    closed = TradeSignal.objects.filter(is_published=True, status__in=['win','loss'])
    wins = closed.filter(status='win').count()
    total = closed.count()
    context = {
        'signals': signals,
        'closed_count': total,
        'win_count': wins,
        'win_rate': round(wins*100/total) if total else None,
        'signals_count': TradeSignal.objects.filter(is_published=True).count(),
        'payment_methods': PaymentMethod.objects.filter(is_active=True, accepts_deposits=True),
    }
    return render(request, 'core/home.html', context)


@require_http_methods(['POST'])
@ratelimit(key='ip', rate='5/h', method='POST', block=False)
def request_subscription(request):
    if getattr(request, 'limited', False):
        messages.error(request, 'تم تجاوز عدد المحاولات. حاول لاحقًا.')
        return redirect('/#pricing')
    full_name = request.POST.get('full_name','').strip()[:120]
    email = request.POST.get('email','').strip()[:254]
    plan = request.POST.get('plan','signals')
    method = request.POST.get('method','usdt')
    try:
        validate_email(email)
    except ValidationError:
        email = ''
    if not full_name or not email or plan not in ['signals','pro'] or method not in ['usdt','gateway']:
        messages.error(request, 'يرجى إدخال البيانات المطلوبة بصورة صحيحة.')
        return redirect('/#pricing')
    PaymentRequest.objects.create(full_name=full_name, email=email, plan=plan, method=method)
    if method == 'gateway':
        messages.success(request, 'تم حفظ طلبك. الدفع الإلكتروني غير مربوط حاليًا وسيتم التواصل معك بعد المراجعة.')
    else:
        messages.success(request, 'تم حفظ طلبك. لا ترسل USDT قبل استلام تعليمات موثوقة والتحقق من عنوان الاستلام.')
    return redirect('/#pricing')
