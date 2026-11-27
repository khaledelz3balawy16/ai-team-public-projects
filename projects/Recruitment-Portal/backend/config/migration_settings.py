"""Explicit opt-in settings using a direct connection; importing never migrates."""
import os

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403
from .database import postgres_database

url = os.environ.get("DATABASE_MIGRATION_URL", "")
if not url:
    raise ImproperlyConfigured("Set DATABASE_MIGRATION_URL to the isolated development database's direct URL.")
DATABASES = {"default": postgres_database(url)}
if "-pooler" in DATABASES["default"]["HOST"]:
    raise ImproperlyConfigured("Use a direct PostgreSQL endpoint for migrations.")
