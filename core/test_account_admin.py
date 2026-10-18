from types import SimpleNamespace

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase

from .admin import AccountProfileAdmin
from .models import AccountProfile, AuditEvent


class AccountProfileAdminPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="account-staff", password="test-only-password", is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username="account-superuser", email="account-admin@example.com", password="test-only-password",
        )
        self.customer = User.objects.create_user(username="account-customer", password="test-only-password")
        self.profile = AccountProfile.objects.create(user=self.customer)
        self.model_admin = AccountProfileAdmin(AccountProfile, AdminSite())

    def test_sensitive_account_controls_are_readonly_for_regular_staff(self):
        request = SimpleNamespace(user=self.staff)
        readonly = self.model_admin.get_readonly_fields(request, self.profile)
        for field in ("user", "status", "can_login", "can_trade", "can_withdraw", "kyc_required"):
            self.assertIn(field, readonly)

    def test_superuser_can_manage_sensitive_account_controls(self):
        request = SimpleNamespace(user=self.superuser)
        readonly = self.model_admin.get_readonly_fields(request, self.profile)
        for field in ("status", "can_login", "can_trade", "can_withdraw", "kyc_required"):
            self.assertNotIn(field, readonly)

    def test_only_superuser_can_delete_account_profile(self):
        self.assertFalse(self.model_admin.has_delete_permission(SimpleNamespace(user=self.staff)))
        self.assertTrue(self.model_admin.has_delete_permission(SimpleNamespace(user=self.superuser)))

    def test_account_changes_record_actor_and_changed_fields(self):
        request = SimpleNamespace(user=self.superuser)
        self.profile.can_trade = True
        form = SimpleNamespace(changed_data=["can_trade"])
        self.model_admin.save_model(request, self.profile, form, change=True)
        event = AuditEvent.objects.get(
            object_type="AccountProfile", object_id=str(self.profile.pk), action="admin_update"
        )
        self.assertEqual(event.actor, self.superuser)
        self.assertIn("can_trade", event.details["changed_fields"])
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.updated_by, self.superuser)
