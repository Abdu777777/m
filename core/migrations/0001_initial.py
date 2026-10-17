from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='PaymentRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=120)),
                ('email', models.EmailField(max_length=254)),
                ('plan', models.CharField(choices=[('signals', 'Signals'), ('pro', 'Pro')], max_length=12)),
                ('method', models.CharField(choices=[('usdt', 'USDT'), ('gateway', 'Online gateway')], max_length=12)),
                ('transaction_reference', models.CharField(blank=True, max_length=180)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('review', 'Under review'), ('paid', 'Paid'), ('rejected', 'Rejected')], default='pending', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('admin_note', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='TradeSignal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=140)),
                ('symbol', models.CharField(help_text='Example: XAU/USD, EUR/USD, BTC/USD', max_length=30)),
                ('market', models.CharField(choices=[('gold', 'Gold'), ('forex', 'Forex'), ('crypto', 'Crypto'), ('indices', 'Indices')], max_length=12)),
                ('direction', models.CharField(choices=[('buy', 'Buy'), ('sell', 'Sell')], max_length=4)),
                ('entry', models.DecimalField(decimal_places=6, max_digits=18)),
                ('stop_loss', models.DecimalField(decimal_places=6, max_digits=18)),
                ('target_1', models.DecimalField(decimal_places=6, max_digits=18)),
                ('target_2', models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True)),
                ('analysis', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('open', 'Open'), ('win', 'Win'), ('loss', 'Loss'), ('cancelled', 'Cancelled')], default='open', max_length=12)),
                ('result_r', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('is_published', models.BooleanField(default=False)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-published_at', '-created_at']},
        ),
    ]
