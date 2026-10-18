from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from .models import TradeSignal, PaymentRequest, PaymentMethod, AccountProfile, KYCSubmission


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


def register(request):
    if request.user.is_authenticated:
        return redirect('account_dashboard')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            AccountProfile.objects.get_or_create(user=user)
            login(request, user)
            return redirect('account_dashboard')
        messages.error(request, 'يرجى مراجعة البيانات وكلمة المرور.')
    else:
        form = UserCreationForm()
    return render(request, 'core/register.html', {'form': form})


@login_required
def account_dashboard(request):
    return render(request, 'core/dashboard.html')


@require_http_methods(['POST'])
@ratelimit(key='ip', rate='5/h', method='POST', block=False)
def request_subscription(request):
    if getattr(request, 'limited', False):
        messages.error(request, 'تم تجاوز عدد المحاولات. حاول لاحقًا.')
        return redirect('/#pricing')
    full_name = request.POST.get('full_name','').strip()[:120]
    email = request.POST.get('email','').strip()[:254]
    plan = request.POST.get('plan','signals')
    method_id = request.POST.get('payment_method_id', '').strip()
    payment_method = PaymentMethod.objects.filter(pk=method_id, is_active=True, accepts_deposits=True).first() if method_id.isdigit() else None
    try:
        validate_email(email)
    except ValidationError:
        email = ''
    if not full_name or not email or plan not in ['signals','pro'] or not payment_method:
        messages.error(request, 'يرجى إدخال البيانات المطلوبة بصورة صحيحة.')
        return redirect('/#pricing')
    legacy_method = 'usdt' if payment_method.kind == 'crypto' else 'gateway'
    PaymentRequest.objects.create(full_name=full_name, email=email, plan=plan, method=legacy_method, payment_method=payment_method, payment_method_snapshot=payment_method.name)
    messages.success(request, 'تم حفظ طلبك لمراجعة الإدارة عبر الوسيلة المحددة. لا ترسل أموالًا قبل تأكيد تعليمات الدفع الرسمية.')
    return redirect('/#pricing')


@login_required
@require_http_methods(['GET', 'POST'])
def kyc_submit(request):
    AccountProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        uploaded = request.FILES.get('document_file')
        if uploaded:
            submission = KYCSubmission(user=request.user, document_type=request.POST.get('document_type', ''), document_file=uploaded, applicant_note=request.POST.get('applicant_note', '').strip()[:500])
            try:
                submission.full_clean()
                submission.save()
                messages.success(request, 'تم استلام طلب التحقق للمراجعة.')
            except ValidationError as exc:
                messages.error(request, 'تعذر قبول المستند: ' + ' '.join(str(x) for x in exc.messages))
        else:
            messages.error(request, 'يرجى اختيار ملف المستند.')
    submissions = KYCSubmission.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'core/kyc.html', {'submissions': submissions})
