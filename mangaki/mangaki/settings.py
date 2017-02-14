"""
Django settings for mangaki project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/
For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os
import configparser
import json
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

config = configparser.ConfigParser(allow_no_value=True, interpolation=None)
config.read(os.path.join(BASE_DIR, 'settings.ini'))

DEBUG = config.getboolean('debug', 'DEBUG', fallback=False)

SECRET_KEY = config.get('secrets', 'SECRET_KEY')

if config.has_section('hosts'):
    ALLOWED_HOSTS = [host.strip() for host in config.get('hosts', 'ALLOWED_HOSTS').split(',')]

SITE_ID = config.getint('deployment', 'SITE_ID', fallback=1)

# Application definition
INSTALLED_APPS = (
    'mangaki',  # Mangaki main application
    'irl',      # Mangaki IRL events
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'bootstrapform',
    'analytical',
    'cookielaw',
    'django_js_reverse',
)

if DEBUG:
    INSTALLED_APPS += (
        'debug_toolbar',
        'django_extensions',
        'django_nose',
    )

    INTERNAL_IPS = ('127.0.0.1',)

    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

    NOSE_ARGS = [
        '--with-doctest'
    ]

    NOTEBOOK_ARGUMENTS = [
        '--ip=0.0.0.0',
    ]

if config.has_section('allauth'):
    INSTALLED_APPS += tuple(
        'allauth.socialaccount.providers.{}'.format(name)
        for name in config.options('allauth')
    )

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

if DEBUG:
    MIDDLEWARE += (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': config.get('pgsql', 'DB_NAME', fallback='mangaki'),
        'USER': config.get('pgsql', 'DB_USER', fallback='django'),
        'PASSWORD': config.get('secrets', 'DB_PASSWORD'),
        'HOST': config.get('pgsql', 'DB_HOST', fallback='127.0.0.1'),
        'PORT': '5432',
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            'templates'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
            'context_processors': [
                'django.template.context_processors.request',
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

EMAIL_BACKEND = config.get('email', 'EMAIL_BACKEND', fallback='django.core.mail.backends.smtp.EmailBackend')
if config.has_section('smtp'):
    EMAIL_HOST = config.get('smtp', 'EMAIL_HOST', fallback='localhost')
    EMAIL_PORT = config.get('smtp', 'EMAIL_PORT', fallback=25)
    EMAIL_HOST_USER = config.get('smtp', 'EMAIL_HOST_USER', fallback='')
    EMAIL_HOST_PASSWORD = config.get('smtp', 'EMAIL_HOST_PASSWORD', fallback='')
    EMAIL_USE_TLS = config.get('smtp', 'EMAIL_USE_TLS', fallback=True)
    EMAIL_USE_SSL = config.get('smtp', 'EMAIL_USE_SSL', fallback=False)
    EMAIL_TIMEOUT = config.get('smtp', 'EMAIL_TIMEOUT', fallback=None)
    EMAIL_SSL_KEYFILE = config.get('smtp', 'EMAIL_SSL_KEYFILE', fallback=None)
    EMAIL_SSL_CERTFILE = config.get('smtp', 'EMAIL_SSL_CERTFILE', fallback=None)

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
LANGUAGE_CODE = 'fr-FR'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

STATIC_ROOT = config.get('deployment', 'STATIC_ROOT', fallback=os.path.join(BASE_DIR, 'static'))
MEDIA_ROOT = config.get('deployment', 'MEDIA_ROOT', fallback=os.path.join(BASE_DIR, 'media'))

# External services
if config.has_section('discourse'):
    DISCOURSE_BASE_URL = config.get('discourse', 'DISCOURSE_BASE_URL')
    DISCOURSE_SSO_SECRET = config.get('secrets', 'DISCOURSE_SSO_SECRET')
    DISCOURSE_API_USERNAME = config.get('discourse', 'DISCOURSE_API_USERNAME')
    DISCOURSE_API_KEY = config.get('secrets', 'DISCOURSE_API_KEY')
    HAS_DISCOURSE = True
else:
    HAS_DISCOURSE = False

if config.has_section('mal'):
    MAL_USER = config.get('mal', 'MAL_USER')
    MAL_PASS = config.get('secrets', 'MAL_PASS')
    MAL_USER_AGENT = config.get('mal', 'MAL_USER_AGENT')

GOOGLE_ANALYTICS_PROPERTY_ID = 'UA-63869890-1'

JS_REVERSE_OUTPUT_PATH = 'mangaki/mangaki/static/js'
