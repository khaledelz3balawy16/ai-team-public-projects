"""Isolated authentication tests: never connect to configured external databases."""
SECRET_KEY = 'CHANGE_ME'
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "rest_framework", "quizapp"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
MIGRATION_MODULES = {"quizapp": None}
ROOT_URLCONF = "quizapp.urls"
USE_TZ = True
LMS_SSO_ENABLED = True
LMS_SSO_SECRET = 'CHANGE_ME'
LMS_BASE_URL = "https://lms.example.test"
FRONTEND_BASE_URL = "https://safeguarding.example.test"
REST_FRAMEWORK = {"UNAUTHENTICATED_USER": None}
