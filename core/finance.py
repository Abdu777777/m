from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .ledger import LedgerValidationError, account_balance, post_ledger_transaction
from .models import AuditEvent, LedgerAccount, LedgerTransaction, MoneyRequest


class MoneyRequestWorkflowError(ValueError):
    """Raised when a financial request cannot safely advance."""


def _require_staff(actor):
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "is_staff", False):
        raise MoneyRequestWorkflowError("A signed-in staff member is required.")


def _ledger_accounts(money_request):
    currency = money_request.currency.strip().upper()
    user_account, _ = LedgerAccount.objects.get_or_create(
        code=f"USER-{money_request.user_id}-{currency}",
        defaults={
            "owner_id": money_request.user_id,
            "kind": LedgerAccount.Kind.USER,
            "currency": currency,
        },
    )
    clearing_account, _ = LedgerAccount.objects.get_or_create(
        code=f"CLEARING-{currency}",
        defaults={"kind": LedgerAccount.Kind.CLEARING, "currency": currency},
    )
    if user_account.owner_id != money_request.user_id or user_account.currency != currency:
        raise MoneyRequestWorkflowError("The user's ledger account does not match this request.")
    if clearing_account.currency != currency:
        raise MoneyRequestWorkflowError("The clearing account currency does not match this request.")
    return user_account, clearing_account


@transaction.atomic
def settle_money_request(*, request_id, actor, evidence_reference, confirm_received=False, confirm_sent=False):
    """
    Record a manually verified deposit or withdrawal in the internal ledger.
    This function never sends funds or calls an external payment provider.
    Deposits require explicit receipt confirmation and a request under review.
    Withdrawals require prior approval, explicit sent confirmation, and a reference.
    """
    _require_staff(actor)
    if not isinstance(evidence_reference, str) or not evidence_reference.strip() or len(evidence_reference.strip()) > 180:
        raise MoneyRequestWorkflowError("A valid external transaction reference is required.")
    evidence_reference = evidence_reference.strip()

    request = MoneyRequest.objects.select_for_update().select_related("user", "payment_method").get(pk=request_id)
    if request.currency.strip().upper() != request.payment_method.currency.strip().upper():
        raise MoneyRequestWorkflowError("Request currency must match the selected payment method.")
    if request.amount <= Decimal("0.00"):
        raise MoneyRequestWorkflowError("Request amount must be positive.")

    if request.kind == MoneyRequest.Kind.DEPOSIT:
        if request.status != MoneyRequest.Status.REVIEW or not confirm_received:
            raise MoneyRequestWorkflowError("A deposit must be under review and explicitly confirmed as received.")
        next_status = MoneyRequest.Status.APPROVED
        idempotency_key = f"money-request-{request.pk}-deposit"
        description = f"Verified deposit for money request #{request.pk}"
    elif request.kind == MoneyRequest.Kind.WITHDRAWAL:
        if request.status != MoneyRequest.Status.APPROVED or not confirm_sent:
            raise MoneyRequestWorkflowError("A withdrawal must be approved and explicitly confirmed as sent.")
        next_status = MoneyRequest.Status.PAID
        idempotency_key = f"money-request-{request.pk}-withdrawal"
        description = f"Verified withdrawal for money request #{request.pk}"
    else:
        raise MoneyRequestWorkflowError("Unsupported money request type.")

    if request.transaction_reference and request.transaction_reference != evidence_reference:
        raise MoneyRequestWorkflowError("The request already has a different transaction reference.")

    user_account, clearing_account = _ledger_accounts(request)
    # Lock the customer account before checking the balance to serialize withdrawals.
    user_account = LedgerAccount.objects.select_for_update().get(pk=user_account.pk)
    if request.kind == MoneyRequest.Kind.WITHDRAWAL and account_balance(user_account) < request.amount:
        raise MoneyRequestWorkflowError("Insufficient ledger balance for this withdrawal.")

    entries = (
        [
            {"account_id": clearing_account.pk, "side": "debit", "amount": request.amount},
            {"account_id": user_account.pk, "side": "credit", "amount": request.amount},
        ]
        if request.kind == MoneyRequest.Kind.DEPOSIT
        else [
            {"account_id": user_account.pk, "side": "debit", "amount": request.amount},
            {"account_id": clearing_account.pk, "side": "credit", "amount": request.amount},
        ]
    )
    try:
        ledger_transaction = post_ledger_transaction(
            idempotency_key=idempotency_key,
            description=description,
            entries=entries,
            created_by=actor,
        )
    except LedgerValidationError as exc:
        raise MoneyRequestWorkflowError(str(exc)) from exc

    previous_status = request.status
    request.status = next_status
    request.transaction_reference = evidence_reference
    request.reviewed_by = actor
    request.reviewed_at = timezone.now()
    request.save(update_fields=("status", "transaction_reference", "reviewed_by", "reviewed_at", "updated_at"))
    AuditEvent.objects.create(
        actor=actor,
        action="money_request_settled",
        object_type="MoneyRequest",
        object_id=str(request.pk),
        details={
            "previous_state": previous_status,
            "new_state": next_status,
            "kind": request.kind,
            "amount": str(request.amount),
            "currency": request.currency,
            "evidence_reference": evidence_reference,
            "ledger_transaction_id": ledger_transaction.pk,
        },
    )
    return request
