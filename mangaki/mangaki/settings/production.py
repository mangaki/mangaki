"""
Production specific settings for Mangaki.

Optimized for performance.
"""

from .common import *

DEBUG = False

ALLOWED_HOSTS = ['mangaki.fr']

INSTALLED_APPS += (
    'allauth.socialaccount.providers.google', # Google Provider
    'allauth.socialaccount.providers.twitter', # Twitter Provider
    'allauth.socialaccount.providers.facebook', # Facebook Provider
)


# Discourse settings
DISCOURSE_BASE_URL = 'http://meta.mangaki.fr'

# Google Analytics
GOOGLE_ANALYTICS_PROPERTY_ID = 'UA-63869890-1'
