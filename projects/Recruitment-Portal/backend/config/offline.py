"""Credential-free schema generation/checks. Never imports runtime settings or .env."""
from .base import *  # noqa: F403

SECRET_KEY = 'CHANGE_ME'
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
CV_PRIVATE_STORAGE_ROOT = BASE_DIR / ".private-test-cvs"
DJANGO_ENV = "offline"
