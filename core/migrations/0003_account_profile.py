import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_platform_configuration'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='AccountProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'بانتظار المراجعة'), ('active', 'نشط'), ('restricted', 'مقيّد'), ('suspended', 'موقوف'), ('closed', 'مغلق')], default='pending', max_length=12)),
                ('can_login', models.BooleanField(default=True)),
                ('can_trade', models.BooleanField(default=False)),
                ('can_withdraw', models.BooleanField(default=False)),
                ('kyc_required', models.BooleanField(default=True)),
                ('restriction_reason', models.CharField(blank=True, max_length=240)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='account_profiles_updated', to=settings.AUTH_USER_MODEL)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='account_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={'permissions': [('manage_account_restrictions', 'Can manage account restrictions'), ('review_kyc', 'Can review identity verification'), ('review_withdrawals', 'Can review withdrawal requests')]},
        ),
    ]
