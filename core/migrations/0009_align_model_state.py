from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0008_support_and_notifications'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='accountprofile',
            options={},
        ),
        migrations.AlterField(
            model_name='accountprofile',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending review'),
                    ('active', 'Active'),
                    ('restricted', 'Restricted'),
                    ('suspended', 'Suspended'),
                    ('closed', 'Closed'),
                ],
                default='pending',
                max_length=12,
            ),
        ),
        migrations.AlterField(
            model_name='tradesignal',
            name='source_timestamp',
            field=models.DateTimeField(
                blank=True,
                help_text='Timestamp of source market data',
                null=True,
            ),
        ),
    ]
