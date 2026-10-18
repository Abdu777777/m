from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from .models import TradeSignal


class TradeSignalValidationTests(TestCase):
    def valid_signal(self, **overrides):
        values = {
            'title': 'EURUSD test',
            'symbol': 'EUR/USD',
            'market': TradeSignal.Market.FOREX,
            'direction': TradeSignal.Direction.BUY,
            'entry': Decimal('1.080000'),
            'stop_loss': Decimal('1.075000'),
            'target_1': Decimal('1.090000'),
            'confidence': 70,
            'review_status': 'approved',
            'is_published': True,
        }
        values.update(overrides)
        return TradeSignal(**values)

    def test_buy_signal_requires_stop_below_entry(self):
        signal = self.valid_signal(stop_loss=Decimal('1.081000'))
        with self.assertRaises(ValidationError):
            signal.full_clean()

    def test_sell_signal_requires_stop_above_entry(self):
        signal = self.valid_signal(
            direction=TradeSignal.Direction.SELL,
            stop_loss=Decimal('1.070000'),
            target_1=Decimal('1.060000'),
        )
        with self.assertRaises(ValidationError):
            signal.full_clean()

    def test_confidence_must_be_between_zero_and_one_hundred(self):
        signal = self.valid_signal(confidence=101)
        with self.assertRaises(ValidationError):
            signal.full_clean()

    def test_unapproved_signal_cannot_remain_published_after_save(self):
        signal = self.valid_signal(review_status='pending', is_published=True)
        signal.save()
        self.assertFalse(signal.is_published)
