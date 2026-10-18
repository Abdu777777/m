from types import SimpleNamespace

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase

from .admin import TradeSignalAdmin
from .models import AuditEvent, TradeSignal


class TradeSignalAdminWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            username="signal-admin-test", email="signal-admin@example.com", password="test-only-password"
        )
        self.model_admin = TradeSignalAdmin(TradeSignal, AdminSite())
        self.model_admin.message_user = lambda *args, **kwargs: None
        self.request = SimpleNamespace(user=self.admin_user)
        self.signal = TradeSignal.objects.create(
            title="Review workflow test", symbol="EUR/USD", market=TradeSignal.Market.FOREX,
            direction=TradeSignal.Direction.BUY, entry="1.100000", stop_loss="1.090000",
            target_1="1.120000", review_status="draft", is_published=False,
        )

    def test_review_approval_and_publication_are_separate_steps(self):
        qs = TradeSignal.objects.filter(pk=self.signal.pk)
        self.model_admin.submit_signals_for_review(self.request, qs)
        self.signal.refresh_from_db()
        self.assertEqual(self.signal.review_status, "pending")
        self.assertFalse(self.signal.is_published)

        self.model_admin.approve_reviewed_signals(self.request, qs)
        self.signal.refresh_from_db()
        self.assertEqual(self.signal.review_status, "approved")
        self.assertFalse(self.signal.is_published)

        self.model_admin.publish_approved_signals(self.request, qs)
        self.signal.refresh_from_db()
        self.assertTrue(self.signal.is_published)
        self.assertIsNotNone(self.signal.published_at)
        self.assertTrue(AuditEvent.objects.filter(
            object_type="TradeSignal", object_id=str(self.signal.pk), action="signal_published"
        ).exists())

    def test_pending_signal_cannot_be_published(self):
        self.signal.review_status = "pending"
        self.signal.save(update_fields=("review_status", "updated_at"))
        self.model_admin.publish_approved_signals(
            self.request, TradeSignal.objects.filter(pk=self.signal.pk)
        )
        self.signal.refresh_from_db()
        self.assertFalse(self.signal.is_published)
        self.assertIsNone(self.signal.published_at)

    def test_rejected_signal_cannot_be_published(self):
        self.signal.review_status = "rejected"
        self.signal.save(update_fields=("review_status", "updated_at"))
        self.model_admin.publish_approved_signals(
            self.request, TradeSignal.objects.filter(pk=self.signal.pk)
        )
        self.signal.refresh_from_db()
        self.assertFalse(self.signal.is_published)

    def test_review_and_publication_fields_are_not_directly_editable(self):
        self.assertIn("review_status", self.model_admin.readonly_fields)
        self.assertIn("is_published", self.model_admin.readonly_fields)
        self.assertNotIn("review_status", self.model_admin.list_editable)
        self.assertNotIn("is_published", self.model_admin.list_editable)

    def test_edit_form_cannot_bypass_review_and_publication_workflow(self):
        self.signal.review_status = "approved"
        self.signal.is_published = True
        form = SimpleNamespace(changed_data=["review_status", "is_published"])
        self.model_admin.save_model(self.request, self.signal, form, change=True)
        self.signal.refresh_from_db()
        self.assertEqual(self.signal.review_status, "draft")
        self.assertFalse(self.signal.is_published)
