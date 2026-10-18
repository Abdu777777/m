import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('core', '0004_payment_method_link'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='LedgerAccount', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('code', models.CharField(max_length=80, unique=True)),
            ('kind', models.CharField(choices=[('user', 'User balance'), ('clearing', 'Payment clearing'), ('fees', 'Fees'), ('system', 'System')], max_length=12)),
            ('currency', models.CharField(default='USD', max_length=12)),
            ('is_active', models.BooleanField(default=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ledger_accounts', to=settings.AUTH_USER_MODEL)),
        ], options={'constraints':[models.CheckConstraint(condition=models.Q(('kind', 'user'), ('owner__isnull', False)) | ~models.Q(('kind', 'user')), name='ledger_user_account_requires_owner')]}),
        migrations.CreateModel(name='LedgerTransaction', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('idempotency_key', models.CharField(max_length=120, unique=True)),
            ('description', models.CharField(max_length=240)),
            ('status', models.CharField(choices=[('posted', 'Posted'), ('reversed', 'Reversed')], default='posted', max_length=12)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name='LedgerEntry', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('side', models.CharField(choices=[('debit', 'Debit'), ('credit', 'Credit')], max_length=6)),
            ('amount', models.DecimalField(decimal_places=2, max_digits=20, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
            ('currency', models.CharField(default='USD', max_length=12)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='entries', to='core.ledgeraccount')),
            ('transaction', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='entries', to='core.ledgertransaction')),
        ], options={'ordering':['created_at','id'], 'constraints':[models.CheckConstraint(condition=models.Q(('amount__gt', 0)), name='ledger_entry_amount_positive')]}),
        migrations.CreateModel(name='MoneyRequest', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('kind', models.CharField(choices=[('deposit', 'Deposit'), ('withdrawal', 'Withdrawal')], max_length=12)),
            ('amount', models.DecimalField(decimal_places=2, max_digits=18, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
            ('currency', models.CharField(default='USD', max_length=12)),
            ('status', models.CharField(choices=[('pending', 'Pending'), ('review', 'Under review'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('paid', 'Paid')], default='pending', max_length=12)),
            ('transaction_reference', models.CharField(blank=True, max_length=180)),
            ('admin_note', models.TextField(blank=True)),
            ('reviewed_at', models.DateTimeField(blank=True, null=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('payment_method', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='money_requests', to='core.paymentmethod')),
            ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_money_requests', to=settings.AUTH_USER_MODEL)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='money_requests', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering':['-created_at']}),
    ]
