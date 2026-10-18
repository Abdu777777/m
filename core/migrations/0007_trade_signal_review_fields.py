from django.db import migrations, models

def mark_existing_published_signals_approved(apps, schema_editor):
    TradeSignal = apps.get_model('core', 'TradeSignal')
    TradeSignal.objects.filter(is_published=True).update(review_status='approved')

class Migration(migrations.Migration):
    dependencies = [('core', '0006_kyc_submission')]
    operations = [
        migrations.AddField(model_name='tradesignal', name='timeframe', field=models.CharField(blank=True, help_text='Example: 5m, 15m, 1h, 4h', max_length=24)),
        migrations.AddField(model_name='tradesignal', name='confidence', field=models.PositiveSmallIntegerField(blank=True, help_text='Analyst confidence, 0-100; not a probability guarantee', null=True)),
        migrations.AddField(model_name='tradesignal', name='source_url', field=models.URLField(blank=True)),
        migrations.AddField(model_name='tradesignal', name='review_status', field=models.CharField(choices=[('draft','Draft'),('pending','Pending review'),('approved','Approved'),('rejected','Rejected')], default='draft', max_length=12)),
        migrations.RunPython(mark_existing_published_signals_approved, migrations.RunPython.noop),
    ]
