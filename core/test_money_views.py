from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import AccountProfile, AuditEvent, MoneyRequest, PaymentMethod


class CustomerMoneyRequestViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="customer-money-view", password="test-only-password")
        self.client.force_login(self.user)
        self.method = PaymentMethod.objects.create(
            name="Customer test wallet", kind=PaymentMethod.Kind.LOCAL, currency="USD",
            is_active=True, accepts_deposits=True, accepts_withdrawals=True,
            minimum_amount=Decimal("5.00"), maximum_amount=Decimal("500.00"),
        )

    def submit(self, **overrides):
        data = {"kind": MoneyRequest.Kind.DEPOSIT, "payment_method_id": str(self.method.pk), "amount": "25.00"}
        data.update(overrides)
        return self.client.post(reverse("money_requests"), data)

    def test_page_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("money_requests"))
        self.assertEqual(response.status_code, 302)

    def test_valid_deposit_creates_pending_request_and_audit_event(self):
        response = self.submit()
        self.assertRedirects(response, reverse("money_requests"))
        item = MoneyRequest.objects.get(user=self.user)
        self.assertEqual(item.status, MoneyRequest.Status.PENDING)
        self.assertEqual(item.currency, "USD")
        self.assertEqual(item.amount, Decimal("25.00"))
        self.assertTrue(AuditEvent.objects.filter(
            action="money_request_created", object_type="MoneyRequest", object_id=str(item.pk)
        ).exists())

    def test_amount_below_payment_method_minimum_is_rejected(self):
        self.submit(amount="1.00")
        self.assertFalse(MoneyRequest.objects.filter(user=self.user).exists())

    def test_amount_above_payment_method_maximum_is_rejected(self):
        self.submit(amount="500.01")
        self.assertFalse(MoneyRequest.objects.filter(user=self.user).exists())

    def test_inactive_payment_method_cannot_be_used(self):
        self.method.is_active = False
        self.method.save(update_fields=("is_active", "updated_at"))
        self.submit()
        self.assertFalse(MoneyRequest.objects.filter(user=self.user).exists())

    def test_withdrawal_requires_account_permission_and_approved_kyc(self):
        AccountProfile.objects.get_or_create(user=self.user)
        self.submit(kind=MoneyRequest.Kind.WITHDRAWAL)
        self.assertFalse(MoneyRequest.objects.filter(user=self.user).exists())

    def test_currency_is_derived_from_selected_payment_method(self):
        method = PaymentMethod.objects.create(
            name="YER test wallet", kind=PaymentMethod.Kind.LOCAL, currency="YER",
            is_active=True, accepts_deposits=True, accepts_withdrawals=False,
            minimum_amount=Decimal("100.00"), maximum_amount=Decimal("100000.00"),
        )
        self.submit(payment_method_id=str(method.pk), amount="250.00")
        item = MoneyRequest.objects.get(user=self.user)
        self.assertEqual(item.currency, "YER")



class MoneyRequestAdminSummaryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="summary-customer", password="test-only-password")
        self.admin_user = User.objects.create_superuser(
            username="summary-admin", email="summary-admin@example.com", password="test-only-password"
        )
        self.method = PaymentMethod.objects.create(
            name="Summary wallet", kind=PaymentMethod.Kind.LOCAL, currency="USD",
            is_active=True, minimum_amount=Decimal("5.00"), maximum_amount=Decimal("500.00"),
        )
        MoneyRequest.objects.create(
            user=self.user, kind=MoneyRequest.Kind.DEPOSIT, amount=Decimal("25.00"),
            currency="USD", payment_method=self.method, status=MoneyRequest.Status.PENDING,
        )
        MoneyRequest.objects.create(
            user=self.user, kind=MoneyRequest.Kind.WITHDRAWAL, amount=Decimal("10.00"),
            currency="USD", payment_method=self.method, status=MoneyRequest.Status.REVIEW,
        )

    def test_admin_changelist_displays_status_kind_and_currency_summary(self):
        self.client.force_login(self.admin_user)
        response = self.client.get("/admin/core/moneyrequest/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ملخص الطلبات المالية")
        self.assertContains(response, "pending")
        self.assertContains(response, "review")
        self.assertContains(response, "deposit")
        self.assertContains(response, "withdrawal")
        self.assertContains(response, "35.00")
