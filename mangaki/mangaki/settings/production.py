"""
Production specific settings for Mangaki.

Optimized for performance.
"""

from .common import *

DEBUG = False

ALLOWED_HOSTS = ['mangaki.fr']

INSTALLED_APPS += (
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.twitter',
    'allauth.socialaccount.providers.facebook',
)


DISCOURSE_BASE_URL = 'http://meta.mangaki.fr'

GOOGLE_ANALYTICS_PROPERTY_ID = 'UA-63869890-1'
