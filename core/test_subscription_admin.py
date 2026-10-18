from types import SimpleNamespace

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase

from .admin import PaymentRequestAdmin
from .models import AuditEvent, PaymentRequest


class SubscriptionPaymentAdminWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            username="subscription-admin-test", email="subscription-admin@example.com", password="test-only-password"
        )
        self.model_admin = PaymentRequestAdmin(PaymentRequest, AdminSite())
        self.model_admin.message_user = lambda *args, **kwargs: None
        self.request = SimpleNamespace(user=self.admin_user)

    def make_payment(self, status=PaymentRequest.Status.PENDING):
        return PaymentRequest.objects.create(
            full_name="Test Subscriber", email="subscriber@example.com",
            plan=PaymentRequest.Plan.SIGNALS, method=PaymentRequest.Method.USDT,
            status=status,
        )

    def test_status_cannot_be_changed_directly(self):
        self.assertIn("status", self.model_admin.readonly_fields)
        self.assertNotIn("status", self.model_admin.list_editable)

    def test_pending_payment_can_be_moved_to_review_and_audited(self):
        pending = self.make_payment()
        paid = self.make_payment(status=PaymentRequest.Status.PAID)
        qs = PaymentRequest.objects.filter(pk__in=[pending.pk, paid.pk])
        self.model_admin.move_selected_to_review(self.request, qs)
        pending.refresh_from_db()
        paid.refresh_from_db()
        self.assertEqual(pending.status, PaymentRequest.Status.REVIEW)
        self.assertEqual(paid.status, PaymentRequest.Status.PAID)
        event = AuditEvent.objects.get(
            object_type="PaymentRequest", object_id=str(pending.pk),
            action="subscription_payment_moved_to_review",
        )
        self.assertEqual(event.details["previous_state"], PaymentRequest.Status.PENDING)
        self.assertEqual(event.details["new_state"], PaymentRequest.Status.REVIEW)

    def test_reject_action_only_rejects_pending_or_review_payments(self):
        pending = self.make_payment()
        review = self.make_payment(status=PaymentRequest.Status.REVIEW)
        paid = self.make_payment(status=PaymentRequest.Status.PAID)
        qs = PaymentRequest.objects.filter(pk__in=[pending.pk, review.pk, paid.pk])
        self.model_admin.reject_selected_payments(self.request, qs)
        pending.refresh_from_db()
        review.refresh_from_db()
        paid.refresh_from_db()
        self.assertEqual(pending.status, PaymentRequest.Status.REJECTED)
        self.assertEqual(review.status, PaymentRequest.Status.REJECTED)
        self.assertEqual(paid.status, PaymentRequest.Status.PAID)
        self.assertEqual(AuditEvent.objects.filter(
            object_type="PaymentRequest", action="subscription_payment_rejected"
        ).count(), 2)

    def test_moving_to_review_never_marks_payment_as_received(self):
        pending = self.make_payment()
        self.model_admin.move_selected_to_review(
            self.request, PaymentRequest.objects.filter(pk=pending.pk)
        )
        pending.refresh_from_db()
        self.assertNotEqual(pending.status, PaymentRequest.Status.PAID)
