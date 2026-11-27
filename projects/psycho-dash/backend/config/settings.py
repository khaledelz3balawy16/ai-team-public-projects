import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'CHANGE_ME')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

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

DATABASE_URL = os.environ.get('DATABASE_URL', '')

if DATABASE_URL:
    import urllib.parse as up
    r = up.urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': r.path.lstrip('/'),
            'USER': r.username,
            'PASSWORD': r.password,
            'HOST': r.hostname,
            'PORT': r.port or 5432,
            'OPTIONS': {'sslmode': 'require'},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── REST Framework ──────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'UNAUTHENTICATED_USER': None,
}

# ── CORS ─────────────────────────────────────────────────────────────────────
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173')
CORS_ALLOWED_ORIGINS = [FRONTEND_URL]
CORS_ALLOW_CREDENTIALS = True

# ── Azure OAuth ──────────────────────────────────────────────────────────────
AZURE_CLIENT_ID     = os.environ.get('AZURE_CLIENT_ID', '')
AZURE_CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET', '')
AZURE_TENANT_ID     = os.environ.get('AZURE_TENANT_ID', '')
AZURE_REDIRECT_URI  = os.environ.get('AZURE_REDIRECT_URI', '')

# ── JWT ───────────────────────────────────────────────────────────────────────
JWT_SECRET_KEY   = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', 8))
AUTH_USER_TABLES = [
    table.strip()
    for table in os.environ.get('AUTH_USER_TABLES', 'user_auth,auth_user').split(',')
    if table.strip()
]

# ── n8n ───────────────────────────────────────────────────────────────────────
N8N_CAREER_WEBHOOK_URL = os.environ.get(
    'N8N_CAREER_WEBHOOK_URL',
    'https://n8n.srv943390.hstgr.cloud/webhook/2bbf6b68-1fd2-4ece-a78c-5c622a9584d4-psychological'
)
N8N_ASSESSMENT_WEBHOOK_TIMEOUT = int(os.environ.get('N8N_ASSESSMENT_WEBHOOK_TIMEOUT', 30))
N8N_ASSESSMENT_WEBHOOK_URLS = {
    'wellbeing': os.environ.get('N8N_WELLBEING_WEBHOOK_URL', ''),
    'psychological': os.environ.get('N8N_PSYCHOLOGICAL_WEBHOOK_URL', ''),
    'personality': os.environ.get('N8N_PERSONALITY_WEBHOOK_URL', ''),
    'career': os.environ.get('N8N_CAREER_ASSESSMENT_WEBHOOK_URL', ''),
    'riasec': os.environ.get('N8N_RIASEC_WEBHOOK_URL', ''),
    'ei': os.environ.get('N8N_EI_WEBHOOK_URL', ''),
    'work': os.environ.get('N8N_WORK_WEBHOOK_URL', ''),
    'cognitive': os.environ.get('N8N_COGNITIVE_WEBHOOK_URL', ''),
    'logical': os.environ.get('N8N_LOGICAL_WEBHOOK_URL', ''),
    'knowledge': os.environ.get('N8N_KNOWLEDGE_WEBHOOK_URL', ''),
    'skills': os.environ.get('N8N_SKILLS_WEBHOOK_URL', ''),
    'behaviors': os.environ.get('N8N_BEHAVIORS_WEBHOOK_URL', ''),
    'learning_style': os.environ.get('N8N_LEARNING_STYLE_WEBHOOK_URL', ''),
}
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
