import hashlib
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.core import signing
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from . import lms_sso
from .models import LMSLoginAttempt
from .views import login_view, admin_login_view, admin_microsoft_callback_view


class LMSSignInTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.verifier = "v" * 43
        self.state = hashlib.sha256(self.verifier.encode()).hexdigest()
        LMSLoginAttempt.objects.create(state=self.state, expires_at=timezone.now() + timedelta(minutes=10))

    def assertion(self, **changes):
        claims = {"aud": "safeguarding", "state": self.state, "account_id": 12, "email": "learner@example.test"}
        claims.update(changes)
        return signing.dumps(claims, key=settings.LMS_SSO_SECRET, salt=lms_sso.SALT)

    def complete(self, assertion=None, verifier=None):
        return lms_sso.complete(self.factory.post("/", {
            "assertion": assertion or self.assertion(), "verifier": verifier or self.verifier,
        }, format="json"))

    def test_login_and_replay(self):
        record = SimpleNamespace(id=9, learner_email="learner@example.test", learner_name="Learner")
        with patch.object(lms_sso, "get_or_create_record", return_value=record) as lookup:
            result = self.complete()
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.data["learner"]["id"], 9)
            self.assertEqual(self.complete().status_code, 401)
            lookup.assert_called_once_with("learner@example.test", "")

    def test_wrong_browser_and_audience_do_not_consume_attempt(self):
        self.assertEqual(self.complete(verifier="x" * 43).status_code, 401)
        self.assertEqual(self.complete(assertion=self.assertion(aud="other-app")).status_code, 401)
        self.assertTrue(LMSLoginAttempt.objects.filter(pk=self.state).exists())

    def test_tampered_expired_and_wrong_key_assertions(self):
        self.assertEqual(self.complete(assertion=self.assertion() + "x").status_code, 401)
        with patch("django.core.signing.time.time", return_value=0):
            expired = self.assertion()
        self.assertEqual(self.complete(assertion=expired).status_code, 401)
        with override_settings(LMS_SSO_SECRET='CHANGE_ME'):
            wrong_key = self.assertion()
        self.assertEqual(self.complete(assertion=wrong_key).status_code, 401)

    def test_expired_attempt(self):
        LMSLoginAttempt.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.complete().status_code, 401)

    def test_new_record_provisioning_and_existing_record_preserved(self):
        with patch.object(lms_sso, "MonitoringRecord") as model, patch.object(lms_sso, "connections"), patch.object(lms_sso.transaction, "atomic"):
            records = model.objects.using.return_value
            records.filter.return_value.order_by.return_value.first.return_value = None
            self.assertEqual(lms_sso.get_or_create_record("new@example.test", "New Learner"), records.create.return_value)
            records.create.assert_called_once_with(learner_email="new@example.test", learner_name="New Learner", organization_name="Kent Business College", completed=False, trigger_count=0)
            records.create.reset_mock()
            existing = SimpleNamespace(id=9, completed=True)
            records.filter.return_value.order_by.return_value.first.return_value = existing
            self.assertIs(lms_sso.get_or_create_record("new@example.test", "Changed Name"), existing)
            records.create.assert_not_called()

    def test_legacy_login_is_disabled(self):
        for view in (login_view, admin_login_view, admin_microsoft_callback_view):
            request = self.factory.get("/") if view == admin_microsoft_callback_view else self.factory.post("/", {"email": "learner@example.test"})
            self.assertEqual(view(request).status_code, 403)

    def test_start_binds_verifier_and_url(self):
        result = lms_sso.start(self.factory.post("/"))
        state = hashlib.sha256(result.data["verifier"].encode()).hexdigest()
        self.assertTrue(LMSLoginAttempt.objects.filter(pk=state).exists())
        self.assertIn("safeguarding_state=" + state, result.data["url"])
        self.assertEqual(result["Cache-Control"], "no-store")

    @override_settings(LMS_SSO_SECRET="")
    def test_missing_configuration_fails_closed(self):
        self.assertEqual(lms_sso.start(self.factory.post("/")).status_code, 503)
        self.assertEqual(self.complete().status_code, 503)
