"""Isolated SSO tests: no environment files or external databases/services."""
SECRET_KEY = 'CHANGE_ME'
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "rest_framework",
    "rest_framework_simplejwt.token_blacklist", "accounts.apps.AccountsConfig",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
ROOT_URLCONF = "accounts.test_lms_sso"
MIDDLEWARE = []
REST_FRAMEWORK = {}
LMS_SSO_ENABLED = True
LMS_SSO_SECRET = 'CHANGE_ME'
LMS_BASE_URL = "https://lms.example.test"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
