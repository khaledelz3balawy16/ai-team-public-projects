import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load local development secrets without requiring an extra dependency.
env_file = BASE_DIR / ".env"
if env_file.exists():
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", 'CHANGE_ME')
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [x for x in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if x]
CSRF_TRUSTED_ORIGINS = [
    x for x in os.getenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
    ).split(",") if x
]
CORS_ALLOWED_ORIGINS = [
    x for x in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
    ).split(",") if x
]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "pmp_assessment",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "config.cors.LocalCorsMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"

if os.getenv("PMP_USE_SQLITE", "false").lower() == "true":
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
elif os.getenv("DATABASE_URL"):
    from urllib.parse import parse_qs, urlparse
    db = urlparse(os.environ["DATABASE_URL"])
    query = parse_qs(db.query)
    DATABASES = {"default": {"ENGINE": 'django.db.backends.CHANGE_MEql', "NAME": db.path.lstrip("/"), "USER": db.username,
                             "PASSWORD": db.password, "HOST": db.hostname, "PORT": db.port or 5432,
                             "OPTIONS": {key: values[-1] for key, values in query.items() if key in {"sslmode", "channel_binding"}}}}
else:
    DATABASES = {"default": {"ENGINE": 'django.db.backends.CHANGE_MEql', "NAME": os.getenv("POSTGRES_DB", "pmp_assessment"),
                             "USER": os.getenv("POSTGRES_USER", 'CHANGE_ME'), "PASSWORD": os.getenv("POSTGRES_PASSWORD", 'CHANGE_ME'),
                             "HOST": os.getenv("POSTGRES_HOST", "localhost"), "PORT": os.getenv("POSTGRES_PORT", "5432")}}

AUTH_PASSWORD_VALIDATORS = []
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "pmp-assessment@example.com")
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["pmp_assessment.authentication.ApiSessionAuthentication"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle", "rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": "30/min", "user": "120/min"},
}



AZURE_PMP_STORAGE_ACCOUNT = os.getenv("AZURE_PMP_STORAGE_ACCOUNT", "kbcdocs")
AZURE_PMP_EXHIBIT_CONTAINER = os.getenv("AZURE_PMP_EXHIBIT_CONTAINER", "pmp-question-assets")
AZURE_PMP_EXHIBIT_READ_SAS = os.getenv("AZURE_PMP_EXHIBIT_READ_SAS", "")
AZURE_PMP_BLOB_BASE_URL = os.getenv(
    "AZURE_PMP_BLOB_BASE_URL",
    f"https://{AZURE_PMP_STORAGE_ACCOUNT}.blob.core.windows.net/{AZURE_PMP_EXHIBIT_CONTAINER}",
).rstrip("/")
AZURE_PMP_EXHIBIT_PROXY_CACHE_SECONDS = int(os.getenv("AZURE_PMP_EXHIBIT_PROXY_CACHE_SECONDS", "300"))
