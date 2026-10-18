from django.test import TestCase
from django.urls import reverse
from .models import PaymentMethod, PaymentRequest, TradeSignal


class PublicPagesTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'عرب أوبشن')
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
