from django.db import models

class TradeSignal(models.Model):
    class Market(models.TextChoices):
        GOLD='gold','Gold'; FOREX='forex','Forex'; CRYPTO='crypto','Crypto'; INDICES='indices','Indices'
    class Direction(models.TextChoices):
        BUY='buy','Buy'; SELL='sell','Sell'
    class Status(models.TextChoices):
        OPEN='open','Open'; WIN='win','Win'; LOSS='loss','Loss'; CANCELLED='cancelled','Cancelled'
    title = models.CharField(max_length=140)
    symbol = models.CharField(max_length=30, help_text='Example: XAU/USD, EUR/USD, BTC/USD')
    market = models.CharField(max_length=12, choices=Market.choices)
    direction = models.CharField(max_length=4, choices=Direction.choices)
    entry = models.DecimalField(max_digits=18, decimal_places=6)
    stop_loss = models.DecimalField(max_digits=18, decimal_places=6)
    target_1 = models.DecimalField(max_digits=18, decimal_places=6)
    target_2 = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True)
    analysis = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    result_r = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-published_at','-created_at']
    def __str__(self): return f'{self.symbol} {self.direction.upper()} — {self.status}'

class PaymentRequest(models.Model):
    class Plan(models.TextChoices):
        SIGNALS='signals','Signals'; PRO='pro','Pro'
    class Method(models.TextChoices):
        USDT='usdt','USDT'; GATEWAY='gateway','Online gateway'
    class Status(models.TextChoices):
        PENDING='pending','Pending'; REVIEW='review','Under review'; PAID='paid','Paid'; REJECTED='rejected','Rejected'
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    plan = models.CharField(max_length=12, choices=Plan.choices)
    method = models.CharField(max_length=12, choices=Method.choices)
    transaction_reference = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    admin_note = models.TextField(blank=True)
    def __str__(self): return f'{self.full_name} — {self.plan} ({self.status})'
