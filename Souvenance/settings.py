"""
Django settings for Souvenance project.
"""

import os
from pathlib import Path

import dotenv


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

dotenv.load_dotenv(os.path.join(BASE_DIR, '.env'))


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("SOUVENANCE_DEBUG", "false").lower() in ("1", "true", "yes")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ValueError("DJANGO_SECRET_KEY doit être renseigné dans le dotenv...")
    SECRET_KEY = "django-insecure-dev-only"

# Liste séparée par des virgules. "*" accepte tout (réseau local).
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("SOUVENANCE_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# URL publique quand on passe par un proxy HTTPS, ex : https://souvenance.exemple.org
# Sans elle, Django refuse les formulaires (CSRF) venant de l'extérieur.
PUBLIC_URL = os.environ.get("SOUVENANCE_PUBLIC_URL", "").strip().rstrip("/")
if PUBLIC_URL:
    CSRF_TRUSTED_ORIGINS = [PUBLIC_URL]
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# Application definition

INSTALLED_APPS = [
    'timeline',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'constance',
    'constance.backends.database'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # sert les fichiers statiques sous gunicorn
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTH_USER_MODEL = 'timeline.User'

ROOT_URLCONF = 'Souvenance.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Souvenance.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get("SOUVENANCE_DB_PATH", BASE_DIR / 'db.sqlite3'),
    }
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization

LANGUAGE_CODE = 'fr-fr'

TIME_ZONE = os.environ.get("TZ", "Europe/Paris")

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # cible de collectstatic (Docker)


# Media files (photos uploadées par les utilisateurs)

MEDIA_URL = 'media/'
MEDIA_ROOT = os.environ.get("SOUVENANCE_MEDIA_ROOT", BASE_DIR / 'media')


# Email

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}


# Constance settings
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'
CONSTANCE_IGNORE_ADMIN_VERSION_CHECK = True

CONSTANCE_CONFIG = {}

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'
