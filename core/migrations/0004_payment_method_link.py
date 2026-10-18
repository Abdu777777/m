from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('core', '0003_account_profile')]
    operations = [
        migrations.AddField(
            model_name='paymentrequest',
            name='payment_method',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_requests', to='core.paymentmethod'),
        ),
        migrations.AddField(
            model_name='paymentrequest',
            name='payment_method_snapshot',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
