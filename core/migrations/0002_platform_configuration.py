import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='AuditEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=80)),
                ('object_type', models.CharField(max_length=80)),
                ('object_id', models.CharField(blank=True, max_length=80)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('kind', models.CharField(choices=[('local', 'محفظة محلية'), ('bank', 'تحويل بنكي'), ('crypto', 'عملة رقمية')], default='local', max_length=12)),
                ('currency', models.CharField(default='USD', max_length=12)),
                ('network', models.CharField(blank=True, max_length=40)),
                ('instructions', models.TextField(blank=True)),
                ('receiving_details', models.TextField(blank=True, help_text='لا تضع مفاتيح خاصة أو بيانات سرية هنا.')),
                ('accepts_deposits', models.BooleanField(default=True)),
                ('accepts_withdrawals', models.BooleanField(default=True)),
                ('minimum_amount', models.DecimalField(decimal_places=2, default=Decimal('5.00'), max_digits=18, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('maximum_amount', models.DecimalField(decimal_places=2, default=Decimal('10000.00'), max_digits=18, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('fee', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=18, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('is_active', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='PlatformSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100, unique=True)),
                ('value', models.JSONField(default=dict)),
                ('description', models.CharField(blank=True, max_length=240)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(model_name='tradesignal', name='source_name', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='tradesignal', name='source_timestamp', field=models.DateTimeField(blank=True, null=True)),
    ]
