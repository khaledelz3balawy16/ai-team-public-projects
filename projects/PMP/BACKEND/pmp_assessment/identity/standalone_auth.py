from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import hashlib
import secrets
from datetime import timedelta
from ..models import KBCPmpLearnerRegistry, LearnerProfile, PMPAuthToken, normalize_email

User = get_user_model()

def token_digest(token): return hashlib.sha256(token.encode("utf-8")).hexdigest()

def issue_token(user, purpose, hours=24):
    raw = secrets.token_urlsafe(32)
    PMPAuthToken.objects.create(user=user, purpose=purpose, token_hash=token_digest(raw), expires_at=timezone.now() + timedelta(hours=hours))
    return raw

def send_account_token(user, purpose, token):
    subject = "Verify your PMP account" if purpose == "email_verification" else "Reset your PMP password"
    message = f"Use this PMP {purpose.replace('_', ' ')} token: {token}"
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)

def consume_token(raw_token, purpose):
    digest = token_digest(raw_token)
    record = PMPAuthToken.objects.select_related("user").filter(purpose=purpose, token_hash=digest, used_at__isnull=True).first()
    if not record or record.expires_at <= timezone.now(): return None
    record.used_at = timezone.now(); record.save(update_fields=["used_at", "updated_at"])
    return record.user

def resolve_kbc_registry(email):
    return KBCPmpLearnerRegistry.objects.filter(normalized_email=normalize_email(email), is_active=True).first()

def create_profile_for_user(user, full_name=""):
    email = normalize_email(user.email)
    registry = resolve_kbc_registry(email)
    if registry:
        return LearnerProfile.objects.create(user=user, user_type="KBC_LEARNER", kbc_registry=registry, name=registry.full_name, email=email,
            programme=registry.programme, cohort=registry.cohort, profile_completed=True, status="active")
    return LearnerProfile.objects.create(user=user, user_type="EXTERNAL", name=full_name, email=email, profile_completed=False, status="active")

def touch_profile(profile):
    profile.last_seen_at = timezone.now()
    profile.save(update_fields=["last_seen_at", "updated_at"])
