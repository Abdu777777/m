from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from types import SimpleNamespace
from .admin import MoneyRequestAdmin
from .models import AuditEvent, MoneyRequest
from django.urls import reverse
from .models import PaymentMethod, PaymentRequest, TradeSignal


class PublicPagesTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Position-size calculator')

    def test_health_endpoint(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_subscription_request_is_saved(self):
        method = PaymentMethod.objects.create(
            name='Test USDT', kind=PaymentMethod.Kind.CRYPTO,
            currency='USDT', is_active=True, accepts_deposits=True,
        )
        response = self.client.post(reverse('request_subscription'), {
            'full_name': 'Test Member', 'email': 'member@example.com',
            'plan': 'signals', 'payment_method_id': str(method.pk),
        })
        self.assertRedirects(response, '/#pricing', fetch_redirect_response=False)
        self.assertEqual(PaymentRequest.objects.count(), 1)
        request = PaymentRequest.objects.get()
        self.assertEqual(request.status, PaymentRequest.Status.PENDING)
        self.assertEqual(request.payment_method, method)

    def test_invalid_subscription_is_rejected(self):
        self.client.post(reverse('request_subscription'), {
            'full_name': '', 'email': 'not-an-email', 'plan': 'unknown',
            'payment_method_id': '999999',
        })
        self.assertEqual(PaymentRequest.objects.count(), 0)

    def test_only_published_signals_are_public(self):
        TradeSignal.objects.create(
            title='Hidden', symbol='XAU/USD', market='gold', direction='buy',
            entry='2000', stop_loss='1990', target_1='2020',
            is_published=False, review_status='draft',
        )
        TradeSignal.objects.create(
            title='Published', symbol='EUR/USD', market='forex', direction='sell',
            entry='1.1', stop_loss='1.11', target_1='1.08',
            is_published=True, review_status='approved',
        )
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'EUR/USD')
        self.assertNotContains(response, 'Hidden')



class MoneyRequestAdminWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='money-customer', password='test-only-password')
        self.admin_user = User.objects.create_superuser(username='money-admin', email='admin@example.com', password='test-only-password')
        self.method = PaymentMethod.objects.create(
            name='Workflow test wallet', kind=PaymentMethod.Kind.LOCAL, currency='USD',
            is_active=True, accepts_deposits=True, accepts_withdrawals=True,
        )
        self.model_admin = MoneyRequestAdmin(MoneyRequest, AdminSite())
        self.model_admin.message_user = lambda *args, **kwargs: None
        self.factory = RequestFactory()

    def make_request(self, kind=MoneyRequest.Kind.DEPOSIT, status=MoneyRequest.Status.PENDING):
        return MoneyRequest.objects.create(
            user=self.user, kind=kind, amount='10.00', currency='USD',
            payment_method=self.method, status=status,
        )

    def test_status_is_not_directly_editable_in_admin(self):
        self.assertIn('status', self.model_admin.readonly_fields)
        self.assertNotIn('status', self.model_admin.list_editable)

    def test_review_action_only_moves_pending_to_review_and_audits(self):
        pending = self.make_request()
        already_rejected = self.make_request(status=MoneyRequest.Status.REJECTED)
        request = self.factory.post('/admin/core/moneyrequest/')
        request.user = self.admin_user
        self.model_admin.mark_selected_for_review(request, MoneyRequest.objects.filter(pk__in=[pending.pk, already_rejected.pk]))
        pending.refresh_from_db()
        already_rejected.refresh_from_db()
        self.assertEqual(pending.status, MoneyRequest.Status.REVIEW)
        self.assertEqual(already_rejected.status, MoneyRequest.Status.REJECTED)
        event = AuditEvent.objects.get(object_type='MoneyRequest', object_id=str(pending.pk), action='money_request_review')
        self.assertEqual(event.details['previous_state'], MoneyRequest.Status.PENDING)
        self.assertEqual(event.details['new_state'], MoneyRequest.Status.REVIEW)

    def test_reject_action_does_not_reject_already_paid_request(self):
        pending = self.make_request()
        paid = self.make_request(status=MoneyRequest.Status.PAID)
        request = self.factory.post('/admin/core/moneyrequest/')
        request.user = self.admin_user
        self.model_admin.reject_selected_requests(request, MoneyRequest.objects.filter(pk__in=[pending.pk, paid.pk]))
        pending.refresh_from_db()
        paid.refresh_from_db()
        self.assertEqual(pending.status, MoneyRequest.Status.REJECTED)
        self.assertEqual(paid.status, MoneyRequest.Status.PAID)
        self.assertTrue(AuditEvent.objects.filter(
            object_type='MoneyRequest', object_id=str(pending.pk), action='money_request_rejected'
        ).exists())
        self.assertFalse(AuditEvent.objects.filter(
            object_type='MoneyRequest', object_id=str(paid.pk), action='money_request_rejected'
        ).exists())
