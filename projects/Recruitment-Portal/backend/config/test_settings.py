"""Disposable in-memory test DB, independent of all runtime connection variables."""
from .offline import *  # noqa: F403

DJANGO_ENV = "test"
RECRUITMENT_ALLOW_SEED = True
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
