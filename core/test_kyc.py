from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.contrib.admin.sites import AdminSite
from types import SimpleNamespace

from .admin import KYCSubmissionAdmin
from .models import KYCSubmission

from .models import validate_kyc_document


class KYCDocumentValidationTests(SimpleTestCase):
    def test_accepts_supported_file_extensions_with_matching_signatures(self):
        samples = {
            "identity.jpg": b"\xff\xd8\xff\xe0test",
            "identity.jpeg": b"\xff\xd8\xff\xe0test",
            "identity.png": b"\x89PNG\r\n\x1a\ntest",
            "identity.pdf": b"%PDF-1.7 test",
        }
        for filename, content in samples.items():
            with self.subTest(filename=filename):
                validate_kyc_document(SimpleUploadedFile(filename, content))

    def test_rejects_unsupported_file_extension(self):
        upload = SimpleUploadedFile("identity.exe", b"test")
        with self.assertRaises(ValidationError):
            validate_kyc_document(upload)

    def test_rejects_content_that_does_not_match_extension(self):
        upload = SimpleUploadedFile("identity.pdf", b"not a PDF")
        with self.assertRaises(ValidationError):
            validate_kyc_document(upload)

    def test_rejects_files_over_five_megabytes(self):
        upload = SimpleUploadedFile("identity.pdf", b"%PDF-" + b"x" * (5 * 1024 * 1024 + 1))
        with self.assertRaises(ValidationError):
            validate_kyc_document(upload)


class KYCAdminPermissionTests(SimpleTestCase):
    def setUp(self):
        self.model_admin = KYCSubmissionAdmin(KYCSubmission, AdminSite())

    def test_regular_staff_cannot_view_kyc_documents(self):
        request = SimpleNamespace(user=SimpleNamespace(
            is_superuser=False,
            has_perm=lambda permission: False,
        ))
        self.assertFalse(self.model_admin.has_view_permission(request))

    def test_reviewer_permission_allows_kyc_admin_access(self):
        request = SimpleNamespace(user=SimpleNamespace(
            is_superuser=False,
            has_perm=lambda permission: permission == "core.review_kycsubmission",
        ))
        self.assertTrue(self.model_admin.has_view_permission(request))

    def test_superuser_can_view_kyc_documents(self):
        request = SimpleNamespace(user=SimpleNamespace(
            is_superuser=True,
            has_perm=lambda permission: False,
        ))
        self.assertTrue(self.model_admin.has_view_permission(request))

    def test_staff_with_change_permission_but_without_reviewer_permission_is_denied(self):
        request = SimpleNamespace(user=SimpleNamespace(
            is_superuser=False,
            has_perm=lambda permission: permission == "core.change_kycsubmission",
        ))
        self.assertFalse(self.model_admin.has_view_permission(request))
        self.assertFalse(self.model_admin.has_change_permission(request))

    def test_reviewer_can_change_kyc_review_status(self):
        request = SimpleNamespace(user=SimpleNamespace(
            is_superuser=False,
            has_perm=lambda permission: permission == "core.review_kycsubmission",
        ))
        self.assertTrue(self.model_admin.has_change_permission(request))
