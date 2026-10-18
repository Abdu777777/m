from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import KYCSubmission


class KYCPrivacyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.customer = User.objects.create_user(
            username="kyc-owner", password="test-only-password"
        )
        self.other_customer = User.objects.create_user(
            username="other-kyc-owner", password="test-only-password"
        )

    @override_settings(MEDIA_ROOT="/tmp/arab-option-kyc-privacy-tests")
    def test_customer_sees_only_their_own_kyc_records_and_no_document_url(self):
        own = KYCSubmission.objects.create(
            user=self.customer,
            document_type=KYCSubmission.DocumentType.NATIONAL_ID,
            document_file=SimpleUploadedFile(
                "identity.pdf", b"%PDF-1.7 private test document", content_type="application/pdf"
            ),
        )
        KYCSubmission.objects.create(
            user=self.other_customer,
            document_type=KYCSubmission.DocumentType.PASSPORT,
            document_file=SimpleUploadedFile(
                "passport.pdf", b"%PDF-1.7 another private document", content_type="application/pdf"
            ),
        )
        self.client.force_login(self.customer)

        response = self.client.get(reverse("kyc_submit"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, own.get_document_type_display())
        self.assertNotContains(response, "Passport")
        self.assertNotContains(response, own.document_file.url)
        self.assertNotContains(response, "private-kyc/")

    @override_settings(MEDIA_ROOT="/tmp/arab-option-kyc-privacy-tests")
    def test_invalid_file_signature_is_rejected(self):
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse("kyc_submit"),
            {
                "document_type": KYCSubmission.DocumentType.NATIONAL_ID,
                "applicant_note": "test",
                "document_file": SimpleUploadedFile(
                    "identity.pdf", b"this is not a PDF", content_type="application/pdf"
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(KYCSubmission.objects.filter(user=self.customer).count(), 0)
        self.assertContains(response, "تعذر قبول المستند")
