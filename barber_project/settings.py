"""
Django settings for barberhub project (base).
"""
import os
from pathlib import Path

import environ

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment variables
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me')
DEBUG = env('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
# ═══════════════════════════════════════════════════════════
# BREVO (Email Service)
# ═══════════════════════════════════════════════════════════
BREVO_API_KEY = os.getenv('BREVO_API_KEY', '')
BREVO_SENDER_EMAIL = os.getenv('BREVO_SENDER_EMAIL', 'noreply@barberhub.com')

# ═══════════════════════════════════════════════════════════
# FRONTEND URL (para links de aceitação de convites)
# ═══════════════════════════════════════════════════════════
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'django_celery_beat',
    'django_celery_results',
    
    # Local apps
    'apps.core',
    'apps.tenants',

    'apps.operacional',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom middlewares (multi-tenant)
    'common.middleware.TenantContextMiddleware',
    'common.middleware.TenantEnforcementMiddleware',
]

ROOT_URLCONF = 'barber_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'barber_project.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',  # ← CORRIGIDO: PostGIS
        'NAME': os.getenv('POSTGRES_DB', 'barber_db'),
        'USER': os.getenv('POSTGRES_USER', 'usuario_postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'senha_postgres'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# Custom User Model
AUTH_USER_MODEL = 'core.Usuario'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.core.jwt.BarberHubJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.StandardPagination',
    'PAGE_SIZE': 20,
}

# Simple JWT
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME', default=60)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        minutes=env.int('JWT_REFRESH_TOKEN_LIFETIME', default=1440)
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'TOKEN_OBTAIN_SERIALIZER': 'apps.core.jwt.BarberHubTokenObtainPairSerializer',
}

# CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# drf-spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'BarberHub SaaS API',
    'DESCRIPTION': 'Plataforma SaaS multi-tenant para gestão de barbearias',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Celery
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'common': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}