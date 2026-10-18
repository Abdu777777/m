from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f'{self.action} {self.object_type}#{self.object_id}'


class PaymentMethod(models.Model):
    class Kind(models.TextChoices):
        LOCAL = 'local', 'محفظة محلية'
        BANK = 'bank', 'تحويل بنكي'
        CRYPTO = 'crypto', 'عملة رقمية'
    name = models.CharField(max_length=100, unique=True)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.LOCAL)
    currency = models.CharField(max_length=12, default='USD')
    network = models.CharField(max_length=40, blank=True)
    instructions = models.TextField(blank=True)
    receiving_details = models.TextField(blank=True, help_text='لا تضع مفاتيح خاصة أو بيانات سرية هنا.')
    accepts_deposits = models.BooleanField(default=True)
    accepts_withdrawals = models.BooleanField(default=True)
    minimum_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('5.00'), validators=[MinValueValidator(Decimal('0.01'))])
    maximum_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('10000.00'), validators=[MinValueValidator(Decimal('0.01'))])
    fee = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['name']
    def __str__(self):
        return f'{self.name} ({self.currency})'


class PlatformSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)
    description = models.CharField(max_length=240, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.key


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
    source_name = models.CharField(max_length=120, blank=True)
    source_timestamp = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    result_r = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-published_at','-created_at']
    def __str__(self):
        return f'{self.symbol} {self.direction.upper()} — {self.status}'


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
    payment_method = models.ForeignKey('PaymentMethod', null=True, blank=True, on_delete=models.SET_NULL, related_name='payment_requests')
    payment_method_snapshot = models.CharField(max_length=100, blank=True)
    def __str__(self):
        return f'{self.full_name} — {self.plan} ({self.status})'


class AccountProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending review'
        ACTIVE = 'active', 'Active'
        RESTRICTED = 'restricted', 'Restricted'
        SUSPENDED = 'suspended', 'Suspended'
        CLOSED = 'closed', 'Closed'
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='account_profile')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    can_login = models.BooleanField(default=True)
    can_trade = models.BooleanField(default=False)
    can_withdraw = models.BooleanField(default=False)
    kyc_required = models.BooleanField(default=True)
    restriction_reason = models.CharField(max_length=240, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='account_profiles_updated')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f'{self.user} - {self.status}'


class LedgerAccount(models.Model):
    class Kind(models.TextChoices):
        USER = 'user', 'User balance'
        CLEARING = 'clearing', 'Payment clearing'
        FEES = 'fees', 'Fees'
        SYSTEM = 'system', 'System'
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='ledger_accounts')
    code = models.CharField(max_length=80, unique=True)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    currency = models.CharField(max_length=12, default='USD')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(kind='user', owner__isnull=False) | ~models.Q(kind='user'), name='ledger_user_account_requires_owner')]
    def __str__(self):
        return f'{self.code} ({self.currency})'


class LedgerTransaction(models.Model):
    class Status(models.TextChoices):
        POSTED = 'posted', 'Posted'
        REVERSED = 'reversed', 'Reversed'
    idempotency_key = models.CharField(max_length=120, unique=True)
    description = models.CharField(max_length=240)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.POSTED)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f'{self.idempotency_key} ({self.status})'


class LedgerEntry(models.Model):
    class Side(models.TextChoices):
        DEBIT = 'debit', 'Debit'
        CREDIT = 'credit', 'Credit'
    transaction = models.ForeignKey(LedgerTransaction, on_delete=models.PROTECT, related_name='entries')
    account = models.ForeignKey(LedgerAccount, on_delete=models.PROTECT, related_name='entries')
    side = models.CharField(max_length=6, choices=Side.choices)
    amount = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.CharField(max_length=12, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='ledger_entry_amount_positive')]
        ordering = ['created_at', 'id']
    def __str__(self):
        return f'{self.side} {self.amount} {self.currency}'


class MoneyRequest(models.Model):
    class Kind(models.TextChoices):
        DEPOSIT = 'deposit', 'Deposit'
        WITHDRAWAL = 'withdrawal', 'Withdrawal'
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        REVIEW = 'review', 'Under review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        PAID = 'paid', 'Paid'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='money_requests')
    kind = models.CharField(max_length=12, choices=Kind.choices)
    amount = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    currency = models.CharField(max_length=12, default='USD')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, related_name='money_requests')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    transaction_reference = models.CharField(max_length=180, blank=True)
    admin_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_money_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f'{self.kind} {self.amount} {self.currency} — {self.status}'


def validate_kyc_document(value):
    import os
    from django.conf import settings
    from django.core.exceptions import ValidationError
    if value.size > getattr(settings, 'KYC_MAX_UPLOAD_BYTES', 5 * 1024 * 1024):
        raise ValidationError('File exceeds the 5 MB limit.')
    if os.path.splitext(value.name)[1].lower() not in {'.jpg', '.jpeg', '.png', '.pdf'}:
        raise ValidationError('Only JPG, PNG and PDF files are accepted.')


def kyc_private_upload_path(instance, filename):
    import uuid
    from pathlib import Path
    return f'private-kyc/{instance.user_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


class KYCSubmission(models.Model):
    class DocumentType(models.TextChoices):
        NATIONAL_ID = 'national_id', 'National ID'
        PASSPORT = 'passport', 'Passport'
        RESIDENCE = 'residence', 'Residence permit'
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending review'
        REVIEW = 'review', 'Under review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='kyc_submissions')
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    document_file = models.FileField(upload_to=kyc_private_upload_path, validators=[validate_kyc_document])
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    applicant_note = models.CharField(max_length=500, blank=True)
    reviewer_note = models.CharField(max_length=500, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_kyc_submissions')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
        permissions = [('review_kycsubmission', 'Can review KYC submissions')]
    def __str__(self):
        return f'KYC {self.user} - {self.status}'
