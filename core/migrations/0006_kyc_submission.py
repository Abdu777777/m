import django.db.models.deletion
import core.models
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_ledger_and_money_requests'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='KYCSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(choices=[('national_id', 'National ID'), ('passport', 'Passport'), ('residence', 'Residence permit')], max_length=20)),
                ('document_file', models.FileField(upload_to=core.models.kyc_private_upload_path, validators=[core.models.validate_kyc_document])),
                ('status', models.CharField(choices=[('pending', 'Pending review'), ('review', 'Under review'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=12)),
                ('applicant_note', models.CharField(blank=True, max_length=500)),
                ('reviewer_note', models.CharField(blank=True, max_length=500)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_kyc_submissions', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='kyc_submissions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at'], 'permissions': [('review_kycsubmission', 'Can review KYC submissions')]},
        ),
    ]
