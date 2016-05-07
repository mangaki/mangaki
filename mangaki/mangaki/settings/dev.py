"""
Django development-specific settings for Mangaki.

This is the file used everytime.
Except in production and staging.
"""

from .common import *

# Dev!
DEBUG = True

# Development-specific apps
INSTALLED_APPS += (
    'debug_toolbar',
)

# Debug email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
