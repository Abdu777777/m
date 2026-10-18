from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .models import validate_kyc_document


class KYCDocumentValidationTests(SimpleTestCase):
    def test_accepts_supported_file_extensions_with_matching_signatures(self):
        samples = {
            "identity.jpg": b"\\xff\\xd8\\xff\\xe0test",
            "identity.jpeg": b"\\xff\\xd8\\xff\\xe0test",
            "identity.png": b"\\x89PNG\\r\\n\\x1a\\ntest",
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
