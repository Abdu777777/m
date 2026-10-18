from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from .ledger import LedgerValidationError, account_balance, post_ledger_transaction
from .models import LedgerAccount, LedgerEntry


class DoubleEntryLedgerTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='ledger-test', password='not-a-real-password')
        self.customer = LedgerAccount.objects.create(owner=self.user, code='USER-TEST-USD', kind='user', currency='USD')
        self.clearing = LedgerAccount.objects.create(code='CLEARING-USD', kind='clearing', currency='USD')

    def test_balanced_transaction_posts_and_updates_derived_balance(self):
        record = post_ledger_transaction(
            idempotency_key='test-deposit-001',
            description='Test deposit',
            entries=[
                {'account_id': self.clearing.id, 'side': 'debit', 'amount': '12.50'},
                {'account_id': self.customer.id, 'side': 'credit', 'amount': '12.50'},
            ],
            created_by=self.user,
        )
        self.assertEqual(record.entries.count(), 2)
        self.assertEqual(account_balance(self.customer), Decimal('12.50'))

    def test_unbalanced_transaction_is_rejected(self):
        with self.assertRaises(LedgerValidationError):
            post_ledger_transaction(
                idempotency_key='test-unbalanced-001',
                description='Invalid transaction',
                entries=[
                    {'account_id': self.clearing.id, 'side': 'debit', 'amount': '10.00'},
                    {'account_id': self.customer.id, 'side': 'credit', 'amount': '9.00'},
                ],
            )
        self.assertEqual(LedgerEntry.objects.count(), 0)

    def test_repeated_idempotency_key_does_not_duplicate_entries(self):
        payload = [
            {'account_id': self.clearing.id, 'side': 'debit', 'amount': '5.00'},
            {'account_id': self.customer.id, 'side': 'credit', 'amount': '5.00'},
        ]
        first = post_ledger_transaction(idempotency_key='same-key', description='Deposit', entries=payload)
        second = post_ledger_transaction(idempotency_key='same-key', description='Deposit', entries=payload)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(LedgerEntry.objects.count(), 2)

    def test_reusing_key_with_different_payload_is_rejected(self):
        post_ledger_transaction(
            idempotency_key='key-conflict',
            description='Deposit',
            entries=[
                {'account_id': self.clearing.id, 'side': 'debit', 'amount': '5.00'},
                {'account_id': self.customer.id, 'side': 'credit', 'amount': '5.00'},
            ],
        )
        with self.assertRaises(LedgerValidationError):
            post_ledger_transaction(
                idempotency_key='key-conflict',
                description='Different amount',
                entries=[
                    {'account_id': self.clearing.id, 'side': 'debit', 'amount': '6.00'},
                    {'account_id': self.customer.id, 'side': 'credit', 'amount': '6.00'},
                ],
            )
