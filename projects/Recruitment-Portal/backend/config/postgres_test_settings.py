"""Optional local PostgreSQL verification; only a loopback, explicitly named test DB."""
import os

from django.core.exceptions import ImproperlyConfigured

from .test_settings import *  # noqa: F403
from .database import postgres_database

db = postgres_database(os.environ.get("TEST_DATABASE_URL", ""))
if db["HOST"] not in ("localhost", "127.0.0.1", "::1") or not db["NAME"].startswith("test_recruitment_"):
    raise ImproperlyConfigured("TEST_DATABASE_URL must target a loopback test_recruitment_* database.")
db["TEST"] = {"NAME": db["NAME"] + "_runner"}
DATABASES = {"default": db}
