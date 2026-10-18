from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .finance import MoneyRequestWorkflowError, settle_money_request
from .ledger import account_balance
from .models import AuditEvent, LedgerAccount, LedgerEntry, MoneyRequest, PaymentMethod


class MoneyRequestSettlementTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.customer = User.objects.create_user(username="finance-customer", password="test-only-password")
        self.staff = User.objects.create_superuser(
            username="finance-admin", email="finance-admin@example.com", password="test-only-password"
        )
        self.method = PaymentMethod.objects.create(
            name="Finance test wallet", kind=PaymentMethod.Kind.LOCAL, currency="USD",
            is_active=True, accepts_deposits=True, accepts_withdrawals=True,
        )

    def make_request(self, kind, status, amount="10.00"):
        return MoneyRequest.objects.create(
            user=self.customer, kind=kind, amount=amount, currency="USD",
            payment_method=self.method, status=status,
        )

    def user_account(self):
        return LedgerAccount.objects.get(code=f"USER-{self.customer.pk}-USD")

    def test_deposit_requires_review_and_explicit_receipt_confirmation(self):
        request = self.make_request(MoneyRequest.Kind.DEPOSIT, MoneyRequest.Status.PENDING)
        with self.assertRaises(MoneyRequestWorkflowError):
            settle_money_request(
                request_id=request.pk, actor=self.staff,
                evidence_reference="deposit-tx-001", confirm_received=True,
            )
        self.assertEqual(LedgerEntry.objects.count(), 0)
        request.refresh_from_db()
        self.assertEqual(request.status, MoneyRequest.Status.PENDING)

    def test_confirmed_deposit_posts_once_and_audits_evidence(self):
        request = self.make_request(MoneyRequest.Kind.DEPOSIT, MoneyRequest.Status.REVIEW, "25.50")
        settled = settle_money_request(
            request_id=request.pk, actor=self.staff,
            evidence_reference="deposit-tx-002", confirm_received=True,
        )
        self.assertEqual(settled.status, MoneyRequest.Status.APPROVED)
        self.assertEqual(settled.transaction_reference, "deposit-tx-002")
        self.assertEqual(account_balance(self.user_account()), Decimal("25.50"))
        self.assertEqual(LedgerEntry.objects.count(), 2)
        audit = AuditEvent.objects.get(action="money_request_settled", object_id=str(request.pk))
        self.assertEqual(audit.details["evidence_reference"], "deposit-tx-002")

    def test_withdrawal_requires_approval_and_sufficient_balance(self):
        request = self.make_request(MoneyRequest.Kind.WITHDRAWAL, MoneyRequest.Status.APPROVED, "10.00")
        with self.assertRaises(MoneyRequestWorkflowError):
            settle_money_request(
                request_id=request.pk, actor=self.staff,
                evidence_reference="withdraw-tx-001", confirm_sent=True,
            )
        self.assertEqual(LedgerEntry.objects.count(), 0)
        request.refresh_from_db()
        self.assertEqual(request.status, MoneyRequest.Status.APPROVED)

    def test_confirmed_withdrawal_debits_ledger_balance(self):
        deposit = self.make_request(MoneyRequest.Kind.DEPOSIT, MoneyRequest.Status.REVIEW, "30.00")
        settle_money_request(
            request_id=deposit.pk, actor=self.staff,
            evidence_reference="deposit-tx-003", confirm_received=True,
        )
        withdrawal = self.make_request(MoneyRequest.Kind.WITHDRAWAL, MoneyRequest.Status.APPROVED, "12.00")
        settled = settle_money_request(
            request_id=withdrawal.pk, actor=self.staff,
            evidence_reference="withdraw-tx-002", confirm_sent=True,
        )
        self.assertEqual(settled.status, MoneyRequest.Status.PAID)
        self.assertEqual(account_balance(self.user_account()), Decimal("18.00"))
        self.assertEqual(LedgerEntry.objects.count(), 4)

    def test_non_staff_cannot_settle_request(self):
        request = self.make_request(MoneyRequest.Kind.DEPOSIT, MoneyRequest.Status.REVIEW)
        with self.assertRaises(MoneyRequestWorkflowError):
            settle_money_request(
                request_id=request.pk, actor=self.customer,
                evidence_reference="deposit-tx-004", confirm_received=True,
            )
        self.assertEqual(LedgerEntry.objects.count(), 0)

    def test_repeated_settlement_does_not_duplicate_ledger_entries(self):
        request = self.make_request(MoneyRequest.Kind.DEPOSIT, MoneyRequest.Status.REVIEW)
        settle_money_request(
            request_id=request.pk, actor=self.staff,
            evidence_reference="deposit-tx-005", confirm_received=True,
        )
        with self.assertRaises(MoneyRequestWorkflowError):
            settle_money_request(
                request_id=request.pk, actor=self.staff,
                evidence_reference="deposit-tx-005", confirm_received=True,
            )
        self.assertEqual(LedgerEntry.objects.count(), 2)
