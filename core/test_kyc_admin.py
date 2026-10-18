from io import BytesIO
from types import SimpleNamespace

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .admin import KYCSubmissionAdmin
from .models import AuditEvent, KYCSubmission


class KYCAdminPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.reviewer = User.objects.create_user(
            username="kyc-reviewer", email="reviewer@example.com", password="test-only-password",
            is_staff=True,
        )
        self.reviewer.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="core", codename="review_kycsubmission"
            )
        )
        self.staff_without_permission = User.objects.create_user(
            username="kyc-no-permission", email="no-permission@example.com",
            password="test-only-password", is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username="kyc-superuser", email="superuser@example.com", password="test-only-password"
        )
        self.model_admin = KYCSubmissionAdmin(KYCSubmission, AdminSite())

    def test_only_authorized_reviewer_or_superuser_can_view_and_change_kyc(self):
        for user in (self.reviewer, self.superuser):
            request = SimpleNamespace(user=user)
            self.assertTrue(self.model_admin.has_view_permission(request))
            self.assertTrue(self.model_admin.has_change_permission(request))
        request = SimpleNamespace(user=self.staff_without_permission)
        self.assertFalse(self.model_admin.has_view_permission(request))
        self.assertFalse(self.model_admin.has_change_permission(request))

    def test_kyc_records_cannot_be_created_or_deleted_from_admin(self):
        request = SimpleNamespace(user=self.superuser)
        self.assertFalse(self.model_admin.has_add_permission(request))
        self.assertFalse(self.model_admin.has_delete_permission(request))

    @override_settings(MEDIA_ROOT="/tmp/kyc-admin-test-media")
    def test_kyc_review_is_audited(self):
        User = get_user_model()
        customer = User.objects.create_user(username="kyc-customer", password="test-only-password")
        submission = KYCSubmission.objects.create(
            user=customer,
            document_type=KYCSubmission.DocumentType.NATIONAL_ID,
            document_file=SimpleUploadedFile("identity.jpg", b"\xff\xd8\xfftest", content_type="image/jpeg"),
        )
        request = SimpleNamespace(user=self.superuser)
        submission.status = KYCSubmission.Status.APPROVED
        form = SimpleNamespace(changed_data=["status"])
        self.model_admin.save_model(request, submission, form, change=True)
        event = AuditEvent.objects.get(
            object_type="KYCSubmission", object_id=str(submission.pk), action="kyc_review"
        )
        self.assertEqual(event.actor, self.superuser)
        self.assertEqual(event.details["previous_state"], KYCSubmission.Status.PENDING)
        self.assertEqual(event.details["new_state"], KYCSubmission.Status.APPROVED)
        submission.refresh_from_db()
        self.assertEqual(submission.reviewed_by, self.superuser)
        self.assertIsNotNone(submission.reviewed_at)
