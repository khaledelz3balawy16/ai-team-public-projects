from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase

from config.database import postgres_database
from recruitment.models import Application, ApplicationStatusHistory, CVDocument


class ConfigurationTests(SimpleTestCase):
    def test_database_requires_tls(self):
        for mode in ("disable", "allow", "prefer"):
            with self.assertRaises(ImproperlyConfigured):
                postgres_database(f"postgresql://CHANGE_ME:CHANGE_ME@localhost:5432/portfolio{mode}")

    def test_database_errors_do_not_echo_credentials(self):
        with self.assertRaises(ImproperlyConfigured) as error:
            postgres_database("invalid://user:sensitive-password@localhost/db")
        self.assertNotIn("sensitive-password", str(error.exception))

    def test_postgresql_configuration_uses_tls_and_psycopg_backend(self):
        db = postgres_database('postgresql://CHANGE_ME:CHANGE_ME@localhost:5432/portfolio')
        self.assertEqual(db["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(db["OPTIONS"]["sslmode"], "require")
        self.assertEqual(db["PASSWORD"], "encoded@secret")

    def test_offline_settings_do_not_read_runtime_environment(self):
        from config import test_settings
        self.assertEqual(test_settings.DATABASES["default"]["ENGINE"], "django.db.backends.sqlite3")
        # Django rewrites :memory: to a shared in-memory URI during test setup.
        self.assertIn(test_settings.DATABASES["default"]["NAME"], (":memory:", "file:memorydb_default?mode=memory&cache=shared"))


class AdminSecurityTests(TestCase):
    def test_anonymous_cannot_access_candidates(self):
        response = self.client.get("/admin/recruitment/applicant/")
        self.assertRedirects(response, "/admin/login/?next=/admin/recruitment/applicant/", fetch_redirect_response=False)

    def test_staff_without_model_permission_cannot_view_candidates(self):
        staff = get_user_model().objects.create_user(username="staff", password='CHANGE_ME', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get("/admin/recruitment/applicant/").status_code, 403)

    def test_sensitive_metadata_and_audit_are_read_only(self):
        from django.test import RequestFactory
        request = RequestFactory().get("/admin/")
        request.user = get_user_model().objects.create_superuser(username="root", password='CHANGE_ME', email="admin@example.test")
        for model in (Application, CVDocument, ApplicationStatusHistory):
            model_admin = admin.site._registry[model]
            self.assertFalse(model_admin.has_add_permission(request))
            self.assertFalse(model_admin.has_change_permission(request))
            self.assertFalse(model_admin.has_delete_permission(request))

    def test_no_public_cv_or_applicant_routes(self):
        for path in ("/api/applicants/", "/api/applications/", "/media/cvs/test.pdf"):
            self.assertEqual(self.client.get(path).status_code, 404)
