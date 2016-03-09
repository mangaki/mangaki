import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'XXX'
DEBUG = True

DISCOURSE_SSO_SECRET = 'XXX'
DISCOURSE_API_USERNAME = 'JJ'
DISCOURSE_API_KEY = 'XXX'

MAL_USER = 'XXX'
MAL_PASS = 'XXX'
MAL_USER_AGENT = 'XXX'

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'mangaki',
        'USER': 'django',
        'PASSWORD': 'XXX',
        'HOST': '127.0.0.1',
        'PORT': '5432'
    }
}

DUMMY = 'XXX'
HASH_PADDLE = 'XXX'

SITE_ID = 1

# Analitycal

GOOGLE_ANALYTICS_PROPERTY_ID = 'UA-63869890-1'
