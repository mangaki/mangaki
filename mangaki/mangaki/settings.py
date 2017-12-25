"""
Django settings for mangaki project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/
For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import configparser
import json
import os
from setuptools_scm import get_version
from pkg_resources import get_distribution, DistributionNotFound
from django.utils.translation import ugettext_lazy as _

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FIXTURE_DIR = os.path.join(os.path.dirname(BASE_DIR), 'fixtures')
TEST_DATA_DIR = os.path.join(BASE_DIR, 'tests', 'data')

config = configparser.ConfigParser(allow_no_value=True, interpolation=None)
config.read(
    os.environ.get('MANGAKI_SETTINGS_PATH', os.path.join(BASE_DIR, 'settings.ini')))

DEBUG = config.getboolean('debug', 'DEBUG', fallback=False)
# Use non-minified version of Vue.js
DEBUG_VUE_JS = config.getboolean('debug', 'DEBUG_VUE_JS', fallback=False)

SECRET_KEY = config.get('secrets', 'SECRET_KEY')

# Step 1: if we are in a Git repository.
try:
    REPO_DIR = os.path.dirname(BASE_DIR)
    VERSION = get_version(REPO_DIR)
except:
    VERSION = None

# Step 2: if we are a nice package.
try:
    if not VERSION:
        VERSION = get_distribution('mangaki').version
except DistributionNotFound:
    VERSION = None

# Otherwise, let the version be unknown.
VERSION = VERSION or 'unknown'


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
    'django.contrib.postgres',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'bootstrap3',
    'django_js_reverse',
    'rest_framework',
    'django_celery_beat'
)

if config.has_section('sentry'):
    import raven

    INSTALLED_APPS += ('raven.contrib.django.raven_compat',)

    RAVEN_CONFIG = {
        'dsn': config.get('sentry', 'dsn')
    }

if config.has_section('allauth'):
    INSTALLED_APPS += tuple(
        'allauth.socialaccount.providers.{}'.format(name)
        for name in config.options('allauth')
    )

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware'
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

if DEBUG:
    INSTALLED_APPS += (
        'debug_toolbar',
        'django_extensions',
        'django_nose',
    )

    INTERNAL_IPS = ('127.0.0.1',)

    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

    NOSE_ARGS = [
        '--with-doctest',
    ]

    NOTEBOOK_ARGUMENTS = [
        '--ip=0.0.0.0',
    ]

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
                'django.template.context_processors.i18n',
                'django.contrib.messages.context_processors.messages',
                'django.contrib.auth.context_processors.auth'
            ],
        }
    }
]


def get_sentry_handler(config_instance) -> str:
    if config_instance.has_section('sentry'):
        return 'raven.contrib.django.raven_compat.handlers.SentryHandler'
    return 'logging.NullHandler'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    # In order for Sentry to catch exceptions and report them.
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'sentry'],
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'sentry': {
            'level': 'ERROR',
            'class': get_sentry_handler(config)
        }
    },
    'loggers': {
        'mangaki': {
            'handlers': ['console', 'sentry'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console', 'sentry'],
            'propagate': False,
        },
        'raven': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        },
        'sentry.errors': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        }
    },
}


ROOT_URLCONF = 'mangaki.urls'
WSGI_APPLICATION = 'mangaki.wsgi.application'

LOGIN_URL = '/user/login/'
LOGIN_REDIRECT_URL = '/'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_SIGNUP_FORM_CLASS = 'mangaki.forms.SignupForm'

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend"
)

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'mosaic_slot_card': '4/sec',
        'mal_import': '3/hour'
    }
}

########################
# Celery configuration #
########################

REDIS_URL = config.get('celery', 'broker_url', fallback='redis://')
CELERY_BROKER_URL = config.get('celery', 'broker_url', fallback='redis://')
CELERY_RESULT_BACKEND = config.get('celery', 'result_backend', fallback='redis://')

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
LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('fr', _('Français')),
    ('en', _('English')),
    ('ja', _('日本語')),
    ('zh-hant', _('中文'))
]
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
DATA_ROOT = config.get('deployment', 'DATA_ROOT', fallback=os.path.join(BASE_DIR, 'data'))

DATA_DIR = DATA_ROOT  # FIXME: replace every occurrence of DATA_DIR with DATA_ROOT
PICKLE_DIR = os.path.join(DATA_ROOT, 'snapshots')  # FIXME: rename PICKLE_DIR to SNAPSHOT_DIR

if config.has_section('sendfile'):
    SENDFILE_BACKEND = config.get('sendfile', 'backend', fallback='sendfile.backends.simple')
    SENDFILE_ROOT = config.get('sendfile', 'root', fallback='')
    SENDFILE_URL = config.get('sendfile', 'url', fallback='')
else:
    SENDFILE_BACKEND = 'sendfile.backends.simple'

# External services
if config.has_section('mal'):
    MAL_USER = config.get('mal', 'MAL_USER')
    MAL_PASS = config.get('secrets', 'MAL_PASS')
    MAL_USER_AGENT = config.get('mal', 'MAL_USER_AGENT')

if config.has_section('anidb'):
    ANIDB_CLIENT = config.get('anidb', 'ANIDB_CLIENT')
    ANIDB_VERSION = config.get('anidb', 'ANIDB_VERSION')

GOOGLE_ANALYTICS_PROPERTY_ID = 'UA-63869890-1'

JS_REVERSE_OUTPUT_PATH = 'mangaki/mangaki/static/js'

RECO_ALGORITHMS_VERBOSE_LEVEL = 1

ANONYMOUS_RATINGS_SESSION_KEY = 'mangaki_ratings'
