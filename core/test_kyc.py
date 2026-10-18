from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .models import validate_kyc_document


class KYCDocumentValidationTests(SimpleTestCase):
    def test_accepts_supported_file_extensions(self):
        for filename in ("identity.jpg", "identity.jpeg", "identity.png", "identity.pdf"):
            with self.subTest(filename=filename):
                upload = SimpleUploadedFile(filename, b"test")
                validate_kyc_document(upload)

    def test_rejects_unsupported_file_extension(self):
        upload = SimpleUploadedFile("identity.exe", b"test")
        with self.assertRaises(ValidationError):
            validate_kyc_document(upload)

    def test_rejects_files_over_five_megabytes(self):
        upload = SimpleUploadedFile("identity.pdf", b"x" * (5 * 1024 * 1024 + 1))
        with self.assertRaises(ValidationError):
            validate_kyc_document(upload)
