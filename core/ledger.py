from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q
from .models import AuditEvent, LedgerAccount, LedgerEntry, LedgerTransaction


class LedgerValidationError(ValueError):
    pass


@transaction.atomic
def post_ledger_transaction(*, idempotency_key, description, entries, created_by=None):
    """
    Post a balanced, multi-entry ledger transaction.
    entries: [{'account_id': int, 'side': 'debit'|'credit', 'amount': Decimal|str}]
    Existing idempotency keys are accepted only if their posted entries match.
    """
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key.strip()) > 120:
        raise LedgerValidationError('A valid idempotency key is required.')
    idempotency_key = idempotency_key.strip()
    if not isinstance(description, str) or not description.strip() or len(description.strip()) > 240:
        raise LedgerValidationError('A transaction description of 1–240 characters is required.')
    if not isinstance(entries, (list, tuple)):
        raise LedgerValidationError('Entries must be a list or tuple.')
    normalized = []
    for item in entries:
        if not isinstance(item, dict):
            raise LedgerValidationError('Each entry must be a mapping.')
        side = item.get('side')
        try:
            amount = Decimal(str(item.get('amount', '0')))
            account_id = int(item['account_id'])
        except (KeyError, TypeError, ValueError, ArithmeticError):
            raise LedgerValidationError('Each entry must have a valid account ID and decimal amount.')
        if not amount.is_finite() or side not in ('debit', 'credit') or amount <= 0 or amount.quantize(Decimal('0.01')) != amount:
            raise LedgerValidationError('Each entry must have a valid side and positive 2-decimal amount.')
        normalized.append({'account_id': account_id, 'side': side, 'amount': amount})
    if len(normalized) < 2:
        raise LedgerValidationError('At least two entries are required.')
    debit_total = sum((e['amount'] for e in normalized if e['side'] == 'debit'), Decimal('0'))
    credit_total = sum((e['amount'] for e in normalized if e['side'] == 'credit'), Decimal('0'))
    if debit_total != credit_total:
        raise LedgerValidationError('Debits and credits must balance exactly.')
    account_ids = sorted({e['account_id'] for e in normalized})
    accounts = list(LedgerAccount.objects.select_for_update().filter(id__in=account_ids, is_active=True).order_by('id'))
    if len(accounts) != len(account_ids):
        raise LedgerValidationError('One or more ledger accounts do not exist or are inactive.')
    account_map = {a.id: a for a in accounts}
    currencies = {account_map[e['account_id']].currency for e in normalized}
    if len(currencies) != 1:
        raise LedgerValidationError('All entries in one transaction must use the same currency.')
    currency = next(iter(currencies))
    existing = LedgerTransaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        current = sorted((e.account_id, e.side, e.amount) for e in existing.entries.all())
        requested = sorted((e['account_id'], e['side'], e['amount']) for e in normalized)
        if existing.status != LedgerTransaction.Status.POSTED:
            raise LedgerValidationError('This idempotency key belongs to a transaction that is not posted.')
        if existing.description != description.strip() or current != requested:
            raise LedgerValidationError('Idempotency key was already used for a different transaction.')
        return existing
    record = LedgerTransaction.objects.create(idempotency_key=idempotency_key, description=description.strip(), created_by=created_by)
    LedgerEntry.objects.bulk_create([
        LedgerEntry(transaction=record, account_id=e['account_id'], side=e['side'], amount=e['amount'], currency=currency)
        for e in normalized
    ])
    AuditEvent.objects.create(
        actor=created_by,
        action='ledger_transaction_posted',
        object_type='LedgerTransaction',
        object_id=str(record.pk),
        details={
            'idempotency_key': idempotency_key,
            'currency': currency,
            'entry_count': len(normalized),
            'debit_total': str(debit_total),
            'credit_total': str(credit_total),
        },
    )
    return record


def account_balance(account):
    """Return a ledger-derived balance; never stores or mutates a balance field."""
    totals = LedgerEntry.objects.filter(account=account).aggregate(
        credits=Sum('amount', filter=Q(side='credit')),
        debits=Sum('amount', filter=Q(side='debit')),
    )
    return (totals['credits'] or Decimal('0')) - (totals['debits'] or Decimal('0'))
