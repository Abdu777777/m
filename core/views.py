from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import TradeSignal, PaymentRequest


def home(request):
    signals = TradeSignal.objects.filter(is_published=True).order_by('-published_at','-created_at')[:6]
    closed = TradeSignal.objects.filter(is_published=True, status__in=['win','loss'])
    wins = closed.filter(status='win').count()
    total = closed.count()
    context = {'signals': signals, 'closed_count': total, 'win_count': wins, 'win_rate': round(wins*100/total) if total else None, 'signals_count': TradeSignal.objects.filter(is_published=True).count()}
    return render(request, 'core/home.html', context)

@require_http_methods(['POST'])
def request_subscription(request):
    full_name = request.POST.get('full_name','').strip()
    email = request.POST.get('email','').strip()
    plan = request.POST.get('plan','signals')
    method = request.POST.get('method','usdt')
    try:
        validate_email(email)
    except ValidationError:
        email = ''
    if not full_name or not email or plan not in ['signals','pro'] or method not in ['usdt','gateway']:
        messages.error(request, 'Please complete all required fields correctly.')
        return redirect('/#pricing')
    PaymentRequest.objects.create(full_name=full_name, email=email, plan=plan, method=method)
    if method == 'gateway':
        messages.success(request, 'Your request is saved. Online gateway checkout is not configured yet; the team must contact you to complete payment.')
    else:
        messages.success(request, 'Your request is saved. USDT payment instructions will be shared privately after review. Never send funds to an unverified address.')
    return redirect('/#pricing')
