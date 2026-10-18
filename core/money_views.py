from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit

from .ledger import account_balance
from .models import AccountProfile, AuditEvent, KYCSubmission, LedgerAccount, MoneyRequest, PaymentMethod


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="10/h", method="POST", block=False)
def money_requests(request):
    AccountProfile.objects.get_or_create(user=request.user)
    methods = PaymentMethod.objects.filter(is_active=True).order_by("name")
    errors = []

    if request.method == "POST":
        if getattr(request, "limited", False):
            messages.error(request, "تم تجاوز عدد المحاولات. حاول لاحقًا.")
            return redirect("money_requests")

        kind = request.POST.get("kind", "").strip()
        method_id = request.POST.get("payment_method_id", "").strip()
        raw_amount = request.POST.get("amount", "").strip()
        method = methods.filter(pk=method_id).first() if method_id.isdigit() else None
        currency = method.currency.strip().upper() if method else ""

        try:
            amount = Decimal(raw_amount)
            if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            amount = None
            errors.append("أدخل مبلغًا موجبًا لا يتجاوز منزلتين عشريتين.")

        if kind not in (MoneyRequest.Kind.DEPOSIT, MoneyRequest.Kind.WITHDRAWAL):
            errors.append("نوع الطلب غير صالح.")
        if method is None:
            errors.append("اختر وسيلة دفع نشطة.")
        elif kind == MoneyRequest.Kind.DEPOSIT and not method.accepts_deposits:
            errors.append("وسيلة الدفع لا تقبل الإيداعات.")
        elif kind == MoneyRequest.Kind.WITHDRAWAL and not method.accepts_withdrawals:
            errors.append("وسيلة الدفع لا تقبل السحب.")
        if method and amount is not None and not (method.minimum_amount <= amount <= method.maximum_amount):
            errors.append(f"المبلغ يجب أن يكون بين {method.minimum_amount} و{method.maximum_amount} {method.currency}.")

        profile = request.user.account_profile
        if kind == MoneyRequest.Kind.WITHDRAWAL:
            if not profile.can_withdraw:
                errors.append("السحب غير مفعّل لحسابك حاليًا.")
            if profile.kyc_required and not KYCSubmission.objects.filter(
                user=request.user, status=KYCSubmission.Status.APPROVED
            ).exists():
                errors.append("يجب اعتماد التحقق من الهوية قبل طلب السحب.")

        if not errors and method and amount is not None:
            with transaction.atomic():
                locked_profile = AccountProfile.objects.select_for_update().get(user=request.user)
                if kind == MoneyRequest.Kind.WITHDRAWAL and not locked_profile.can_withdraw:
                    errors.append("السحب غير مفعّل لحسابك حاليًا.")
                if kind == MoneyRequest.Kind.WITHDRAWAL and not errors:
                    account = LedgerAccount.objects.select_for_update().filter(
                        owner=request.user, currency=currency, kind=LedgerAccount.Kind.USER, is_active=True
                    ).first()
                    balance = account_balance(account) if account else Decimal("0.00")
                    held = MoneyRequest.objects.filter(
                        user=request.user, kind=MoneyRequest.Kind.WITHDRAWAL, currency=currency,
                        status__in=(MoneyRequest.Status.PENDING, MoneyRequest.Status.REVIEW, MoneyRequest.Status.APPROVED),
                    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
                    if amount + held > balance:
                        errors.append("الرصيد المتاح لا يغطي السحب بعد احتساب الطلبات المعلّقة.")
                if not errors:
                    item = MoneyRequest.objects.create(
                        user=request.user, kind=kind, amount=amount, currency=currency, payment_method=method
                    )
                    AuditEvent.objects.create(
                        actor=request.user, action="money_request_created",
                        object_type="MoneyRequest", object_id=str(item.pk),
                        details={"kind": kind, "amount": str(amount), "currency": currency, "payment_method_id": method.pk},
                    )
                    messages.success(request, "تم إرسال طلبك للمراجعة. لا يتم تنفيذ أي تحويل تلقائيًا.")
                    return redirect("money_requests")

        for error in errors:
            messages.error(request, error)

    items = MoneyRequest.objects.filter(user=request.user).select_related("payment_method")[:50]
    return render(request, "core/money_requests.html", {"payment_methods": methods, "money_requests": items})
