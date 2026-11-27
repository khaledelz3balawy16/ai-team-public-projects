"""Browser-bound, single-use login assertions issued by the LMS."""
import hashlib
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.db import connections, transaction
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .auth import create_login_token
from .models import LMSLoginAttempt, MonitoringRecord

SALT = "kbc-safeguarding-sso-v1"


def configured():
    return settings.LMS_SSO_ENABLED and len(settings.LMS_SSO_SECRET) >= 32


def get_or_create_record(email, display_name):
    # Existing WSMS records have no unique email constraint. Serialize provisioning
    # by normalized email across workers without changing the external table.
    lock_id = int.from_bytes(hashlib.sha256(email.encode()).digest()[:8], "big", signed=True)
    with transaction.atomic(using="wsms"):
        with connections["wsms"].cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])
        records = MonitoringRecord.objects.using("wsms")
        record = records.filter(learner_email__iexact=email).order_by("id").first()
        if record is None:
            record = records.create(
                learner_email=email, learner_name=display_name or email,
                organization_name="Kent Business College", completed=False, trigger_count=0,
            )
        return record


@api_view(["GET"])
def config(request):
    return Response({"enabled": settings.LMS_SSO_ENABLED})


@api_view(["POST"])
def start(request):
    if not configured():
        return Response({"detail": "LMS sign-in is not configured."}, status=503)
    verifier = secrets.token_urlsafe(32)
    state = hashlib.sha256(verifier.encode()).hexdigest()
    LMSLoginAttempt.objects.filter(expires_at__lte=timezone.now()).delete()
    LMSLoginAttempt.objects.create(state=state, expires_at=timezone.now() + timedelta(minutes=10))
    response = Response({
        "verifier": verifier,
        "url": settings.LMS_BASE_URL + "/login?" + urlencode({"safeguarding_state": state}),
    })
    response["Cache-Control"] = "no-store"
    return response


@api_view(["POST"])
def complete(request):
    if not configured():
        return Response({"detail": "LMS sign-in is not configured."}, status=503)
    assertion = request.data.get("assertion", "")
    verifier = request.data.get("verifier", "")
    if not isinstance(assertion, str) or not isinstance(verifier, str) or not 40 <= len(verifier) <= 128:
        return Response({"detail": "Invalid login response."}, status=400)
    state = hashlib.sha256(verifier.encode()).hexdigest()
    try:
        claims = signing.loads(assertion, key=settings.LMS_SSO_SECRET, salt=SALT, max_age=60, fallback_keys=[])
    except signing.BadSignature:
        return Response({"detail": "LMS sign-in expired or is invalid. Please sign in again."}, status=401)
    if (not isinstance(claims, dict) or claims.get("aud") != "safeguarding"
            or claims.get("state") != state or not claims.get("account_id")
            or not isinstance(claims.get("email"), str) or not claims["email"].strip()
            or not isinstance(claims.get("display_name", ""), str)):
        return Response({"detail": "Invalid login response."}, status=401)
    # DELETE is atomic across workers: exactly one request can consume the attempt.
    with transaction.atomic():
        consumed, _ = LMSLoginAttempt.objects.filter(state=state, expires_at__gt=timezone.now()).delete()
    if not consumed:
        return Response({"detail": "Login has expired or was already used. Please sign in again."}, status=401)
    email = claims["email"].strip().lower()
    record = get_or_create_record(email, claims.get("display_name", ""))
    response = Response({
        "token": create_login_token(record),
        "learner": {"id": record.id, "email": record.learner_email, "full_name": record.learner_name or ""},
        "next_route": "/onboarding",
    })
    response["Cache-Control"] = "no-store"
    return response
