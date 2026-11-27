import os

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from .base import *  # noqa: F403
from .database import postgres_database

load_dotenv(BASE_DIR / ".env")
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY to a random secret of at least 50 characters.")
DJANGO_ENV = os.environ.get("DJANGO_ENV", "production")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
if DEBUG and DJANGO_ENV != "development":
    raise ImproperlyConfigured("Debug mode is only allowed in development.")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
DATABASES = {"default": postgres_database(os.environ.get("DATABASE_URL", ""))}
CV_PRIVATE_STORAGE_ROOT = os.environ.get("CV_PRIVATE_STORAGE_ROOT", "")
if not CV_PRIVATE_STORAGE_ROOT or not Path(CV_PRIVATE_STORAGE_ROOT).is_absolute():
    raise ImproperlyConfigured("Set CV_PRIVATE_STORAGE_ROOT to an absolute private path outside web roots.")
RECRUITMENT_ALLOW_SEED = (
    DJANGO_ENV == "development"
    and os.environ.get("RECRUITMENT_ALLOW_SEED", "false").lower() == "true"
)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
