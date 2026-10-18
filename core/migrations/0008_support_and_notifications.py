import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('core', '0007_trade_signal_review_fields'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='SupportTicket', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('subject', models.CharField(max_length=160)),
            ('message', models.TextField(max_length=5000)),
            ('status', models.CharField(choices=[('open','Open'),('in_progress','In progress'),('waiting','Waiting for user'),('resolved','Resolved'),('closed','Closed')], default='open', max_length=16)),
            ('priority', models.CharField(choices=[('low','Low'),('normal','Normal'),('high','High')], default='normal', max_length=10)),
            ('staff_note', models.TextField(blank=True, max_length=3000)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_support_tickets', to=settings.AUTH_USER_MODEL)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='support_tickets', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering':['-updated_at']}),
        migrations.CreateModel(name='UserNotification', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('title', models.CharField(max_length=160)),
            ('message', models.CharField(max_length=1000)),
            ('category', models.CharField(default='general', max_length=32)),
            ('target_url', models.CharField(blank=True, max_length=300)),
            ('is_read', models.BooleanField(default=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('read_at', models.DateTimeField(blank=True, null=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='platform_notifications', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering':['-created_at']}),
    ]
