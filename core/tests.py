from django.test import TestCase, Client
from django.urls import reverse
from .models import TradeSignal, PaymentRequest

class PublicPagesTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ASTRATRADE')
        self.assertContains(response, 'Position-size calculator')

    def test_health_endpoint(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_subscription_request_is_saved(self):
        response = self.client.post(reverse('request_subscription'), {
            'full_name': 'Test Member', 'email': 'member@example.com',
            'plan': 'signals', 'method': 'usdt'
        })
        self.assertRedirects(response, '/#pricing', fetch_redirect_response=False)
        self.assertEqual(PaymentRequest.objects.count(), 1)
        self.assertEqual(PaymentRequest.objects.get().status, PaymentRequest.Status.PENDING)

    def test_invalid_subscription_is_rejected(self):
        self.client.post(reverse('request_subscription'), {
            'full_name': '', 'email': 'not-an-email', 'plan': 'unknown', 'method': 'usdt'
        })
        self.assertEqual(PaymentRequest.objects.count(), 0)

    def test_only_published_signals_are_public(self):
        TradeSignal.objects.create(title='Hidden', symbol='XAU/USD', market='gold', direction='buy', entry='2000', stop_loss='1990', target_1='2020', is_published=False)
        TradeSignal.objects.create(title='Published', symbol='EUR/USD', market='forex', direction='sell', entry='1.1', stop_loss='1.11', target_1='1.08', is_published=True)
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'EUR/USD')
        self.assertNotContains(response, 'Hidden')
