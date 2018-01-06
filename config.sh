#!/bin/bash

# PostgreSQL
createdb mangaki
createuser django
export DB_PASSWORD=$(pwgen -s -c 30 1)
psql -d mangaki -c \
  "alter user django with password '$DB_PASSWORD'; \
  grant all privileges on database mangaki to django; \
  create extension if not exists pg_trgm; \
  create extension if not exists unaccent"

# Config file
cat > mangaki/settings.ini <<EOF
[debug]
DEBUG = True
DEBUG_VUE_JS = True

[secrets]
SECRET_KEY = $(pwgen -s -c 60 1)
DB_PASSWORD = ${DB_PASSWORD}

[celery]
BROKER_URL = redis://
RESULT_BACKEND = redis://

[email]
EMAIL_BACKEND = django.core.mail.backends.console.EmailBackend
EOF
