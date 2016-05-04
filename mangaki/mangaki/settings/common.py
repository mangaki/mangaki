"""
Common Django settings for Mangaki project.
All settings can be overriden following the current environment.

(look APP_SETTINGS to load a different environment)
"""

import os
from secret import SECRET_KEY, DISCOURSE_SSO_SECRET, DATABASES
BASE_DIR = os.path.dirname(os.path.dirname(__file__)) # Base path of the project.

# Application definition
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'mangaki', # Mangaki main application
    'irl', # Mangaki IRL application for events
    'allauth', # Authentication helper
    'allauth.account', 
    'allauth.socialaccount',
    'bootstrapform', # Bootstrap form helper
    'analytical', # Google Analytics helper (analytics service)
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            'templates'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.core.context_processors.request',
                'django.template.context_processors.static',
                'django.template.context_processors.media',
                'django.template.context_processors.debug',
                'django.contrib.messages.context_processors.messages',
                'django.contrib.auth.context_processors.auth'
            ],
        }
    }
]

ROOT_URLCONF = 'mangaki.urls'
WSGI_APPLICATION = 'mangaki.wsgi.application'

LOGIN_URL = '/user/login/'
LOGIN_REDIRECT_URL = '/'
ACCOUNT_EMAIL_REQUIRED = True

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend"
)

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/
LANGUAGE_CODE = 'fr-FR'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = '/srv/http/mangaki/static/'
