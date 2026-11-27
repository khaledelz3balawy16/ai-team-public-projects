import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'CHANGE_ME')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = [host.strip() for host in os.environ.get('ALLOWED_HOSTS', 'localhost').split(',') if host.strip()]

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'psycho',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

# ── Database (Neon PostgreSQL) ──────────────────────────────────────────────
import dj_database_url  # installed via pip if needed, OR parse manually

import urllib.parse as up


def _postgres_config_from_url(database_url: str) -> dict:
    """Parse a postgres:// connection string into a Django DATABASES entry."""
    r = up.urlparse(database_url)
    query_options = dict(up.parse_qsl(r.query))
    db_options = {'sslmode': query_options.get('sslmode', 'require')}
    if query_options.get('channel_binding'):
        db_options['channel_binding'] = query_options['channel_binding']

    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': r.path.lstrip('/'),
        'USER': r.username,
        'PASSWORD': r.password,
        'HOST': r.hostname,
        'PORT': r.port or 5432,
        'OPTIONS': db_options,
    }


DATABASE_URL = os.environ.get('DATABASE_URL', '')

if DATABASE_URL:
    DATABASES = {'default': _postgres_config_from_url(DATABASE_URL)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── KBC users database (read-only lookup for ?email= redirect login) ─────────
# A separate database (the WordPress/Kent users store) holding kbc_users_data.
# Used only to resolve a learner's id + name + email from their email address.
USER_DATABASE_URL = os.environ.get('USER_DATABASE_URL', '')
if USER_DATABASE_URL:
    DATABASES['users'] = _postgres_config_from_url(USER_DATABASE_URL)

# AiTeamKBC — source-of-truth learner database (aptem_auto_extracting)
APTEM_DATABASE_URL = os.environ.get('APTEM_DATABASE_URL', '')
if APTEM_DATABASE_URL:
    DATABASES['aptem'] = _postgres_config_from_url(APTEM_DATABASE_URL)

# Table + columns to read the learner identity from. Column names are
# case-sensitive (quoted) in the KBC users database.
KBC_USERS_TABLE = os.environ.get('KBC_USERS_TABLE', 'kbc_users_data')
KBC_USERS_ID_COLUMN = os.environ.get('KBC_USERS_ID_COLUMN', 'ID')
KBC_USERS_NAME_COLUMN = os.environ.get('KBC_USERS_NAME_COLUMN', 'FullName')
KBC_USERS_EMAIL_COLUMN = os.environ.get('KBC_USERS_EMAIL_COLUMN', 'Email')

# When True, the ?email= redirect login only succeeds if the email exists in
# kbc_users_data. Leave False in local dev (so the public demo email works).
KBC_REQUIRE_KNOWN_EMAIL = os.environ.get('KBC_REQUIRE_KNOWN_EMAIL', 'False') == 'True'

# ── REST Framework ──────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'psycho.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'UNAUTHENTICATED_USER': None,
}

# ── CORS ─────────────────────────────────────────────────────────────────────
FRONTEND_URL = os.environ.get(
    'FRONTEND_URL',
    'http://localhost:5173' if DEBUG else 'https://who-i-am.kentbusinesscollege.net',
)
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CORS_ALLOWED_ORIGINS', FRONTEND_URL).split(',')
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True
PUBLIC_DASHBOARD_ENABLED = os.environ.get(
    'PUBLIC_DASHBOARD_ENABLED',
    'True' if DEBUG else 'False',
) == 'True'

# ── Azure OAuth ──────────────────────────────────────────────────────────────
AZURE_CLIENT_ID     = os.environ.get('AZURE_CLIENT_ID', '')
AZURE_CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET', '')
AZURE_TENANT_ID     = os.environ.get('AZURE_TENANT_ID', '')
AZURE_REDIRECT_URI  = os.environ.get(
    'AZURE_REDIRECT_URI',
    'http://localhost:8000/api/auth/callback/' if DEBUG else '',
)
MS_REDIRECT_URI     = os.environ.get(
    'MS_REDIRECT_URI',
    'http://localhost:8000/api/accounts/callback' if DEBUG else '',
)

# ── JWT ───────────────────────────────────────────────────────────────────────
JWT_SECRET_KEY   = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', 8))
AUTH_USER_TABLES = [
    table.strip()
    for table in os.environ.get('AUTH_USER_TABLES', 'user_auth,auth_user').split(',')
    if table.strip()
]

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL   = os.environ.get('OPENAI_MODEL', 'gpt-4o')

ASSESSMENT_QUIZ_LINKS = {
    'wellbeing': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=wellbeing',
    'psychological': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=psychological',
    'personality': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=personality',
    'career': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Career%20Adaptability',
    'riasec': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Career%20Interests%20(RIASEC)',
    'ei': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Emotional%20Intelligence%20(EI)',
    'work': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Work%20Values',
    'cognitive': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=English',
    'logical': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Mathematics',
    'knowledge': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Knowledge%20Assessment',
    'skills': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Skills%20Assessment',
    'behaviors': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Behaviours%20Assessment',
    'learning_style': 'https://kentbusinesscollege.org/self_assessment_quiz/?type=learning_style',
}

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_TZ        = True

TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': []}}]
