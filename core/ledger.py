from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q
from .models import LedgerAccount, LedgerEntry, LedgerTransaction


class LedgerValidationError(ValueError):
    pass


@transaction.atomic
def post_ledger_transaction(*, idempotency_key, description, entries, created_by=None):
    """
    Post a balanced, multi-entry ledger transaction.
    entries: [{'account_id': int, 'side': 'debit'|'credit', 'amount': Decimal|str}]
    Existing idempotency keys are accepted only if their posted entries match.
    """
    if not idempotency_key or len(idempotency_key) > 120:
        raise LedgerValidationError('A valid idempotency key is required.')
    normalized = []
    for item in entries:
        side = item.get('side')
        amount = Decimal(str(item.get('amount', '0')))
        if side not in ('debit', 'credit') or amount <= 0 or amount.quantize(Decimal('0.01')) != amount:
            raise LedgerValidationError('Each entry must have a valid side and positive 2-decimal amount.')
        normalized.append({'account_id': int(item['account_id']), 'side': side, 'amount': amount})
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
        if existing.description != description or current != requested:
            raise LedgerValidationError('Idempotency key was already used for a different transaction.')
        return existing
    record = LedgerTransaction.objects.create(idempotency_key=idempotency_key, description=description[:240], created_by=created_by)
    LedgerEntry.objects.bulk_create([
        LedgerEntry(transaction=record, account_id=e['account_id'], side=e['side'], amount=e['amount'], currency=currency)
        for e in normalized
    ])
    return record


def account_balance(account):
    """Return a ledger-derived balance; never stores or mutates a balance field."""
    totals = LedgerEntry.objects.filter(account=account).aggregate(
        credits=Sum('amount', filter=Q(side='credit')),
        debits=Sum('amount', filter=Q(side='debit')),
    )
    return (totals['credits'] or Decimal('0')) - (totals['debits'] or Decimal('0'))
