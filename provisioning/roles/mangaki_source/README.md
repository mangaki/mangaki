# Mangaki source code

This role installs and configures the Mangaki codebase on a server.

## Dependencies

This role doesn't have any dependencies and can be used in a standalone way on
any server. As it doesn't *do* anything in itself; it will usually be used in
conjunction with one or several roles that extends it such as the
[`mangaki_front`](../mangaki_front/README.md) or
[`mangaki_back`](../mangaki_back/README.md) role.

NOTE: Most of the time, you will want to use the
[`mangaki_sync`](../mangaki_sync/README.md) role right after this one, as it
takes care of migrating the database and ensuring that subsequent roles will be
able to properly function. In the future, the database migration handling
should happen in this role instead.

## Role variables

This role accepts the following parameters:

```yaml
#########################
# General configuration #
#########################

# Unix account under which Mangaki should be set up.
mangaki_source_user: 'mangaki'

# Unix group for mangaki_source_user
mangaki_source_group: 'mangaki'

# Home directory for mangaki_source_user
mangaki_source_home: '/home/mangaki'

# Path to the virtualenv into which Mangaki should be installed.
mangaki_source_venv_path: '{{ mangaki_source_home }}/venv'

# Mangaki's installation type. Valid values are:
# - 'pypi': Install mangaki from PyPI. In that case, 'mangaki_source_package'
#   must be the name of the version to install, in pip format.
# - 'copy': Install an existing packaged version of mangaki present on the
#   coordinator. In that case, `mangaki_source_package_local` must be the path
#   to the existing package on the ansible coordinator and
#   `mangaki_source_package` the path  to which the package should be copied on
#   the host.
# - 'develop': Install a development version of mangaki. In that case,
#   `mangaki_source_package` must be the path to the Mangaki repository (containing
#   the `setup.py` script) on the host. Note that this role will *NOT* copy the
#   source code to that location -- this parameter is intended for development
#   machines (in particular, Vagrant boxes) and it is the user's responsibility
#   to ensure the source code is in place prior to running the playbook.
mangaki_source_install_type: 'pypi'

# Mangaki package to install. See `mangaki_source_install_type` for possible
# values.
mangaki_source_package: 'mangaki==0.2'

# Local path to a pre-built Mangaki package (required when
# mangaki_source_install_type is "copy").
mangaki_source_package_local: 'mangaki-0.2.tar.gz'

# Path to where the settings.ini configuration file should be placed.
mangaki_source_settings_path: '/home/mangaki/settings.ini'

########################
# Django configuration #
########################

# Should debug mode be enabled? Activating this will also install necessary
# development-only packages.
mangaki_source_debug: false

# Secret key (required)
mangaki_secret_key: 'explosion'

# Auth providers to enable
mangaki_source_auth_providers: ['twitter', 'facebook']

#####################
# Web configuration #
#####################

# The path to the web root to store static files in (required).
mangaki_source_static_root: '/var/www/mangaki/static'

# The path to the web root to store data and snapshots in (required).
mangaki_source_data_root: '/var/www/mangaki/data'

# The list of domains this instance is allowed to serve (required).
mangaki_source_domains: ['mangaki.fr', 'www.mangaki.fr']


##########################
# Database configuration #
##########################

# Database host to connect to.
mangaki_source_db_host: '127.0.0.1'

# Database user.
mangaki_source_db_user: 'mangaki'

# Database name.
mangaki_source_db_name: 'mangaki'

# Database password (required).
mangaki_source_db_password: 'tuturuu'

#######################
# Redis configuration #
#######################

# Redis host to connect to.
mangaki_source_redis_host: '127.0.0.1'

# Redis port to connect to.
mangaki_source_redis_port: 6379

# Redis database index (default to 0)
mangaki_source_redis_database: 0

# Redis password (not required, if Redis does not have password)
mangaki_source_redis_password: 'madscientist'

#######################
# Email configuration #
#######################

# Whether to enable an email provider. If disabled, mails will be written to
# the console instead; defaults to false when mangaki_source_debug is enabled.
mangaki_source_has_email: true

# Address of the email server to use.
mangaki_source_email_host: '127.0.0.1'

# Connect to this port of the email server.
mangaki_source_email_port: 587

# Username to use for connecting to the email server (required if
# mangaki_source_has_email is enabled).
mangaki_source_email_user: 'mangaki'

# Password to use for connecting to the email server (required if
# mangaki_source_has_email is enabled).
mangaki_source_email_password: 'hero4fun'

######################################
# MyAnimeList integration (optional) #
######################################

# Whether to enable MAL integration.
mangaki_source_has_mal: false

# Username for connecting to the MAL API (required if mangaki_source_has_mal is
# enabled).
mangaki_source_mal_user: 'mangaki'

# User Agent for connecting to the MAL API (required if mangaki_source_has_mal
# is enabled).
mangaki_source_mal_user_agent: 'mangaki 0.1.4'

# Password for connecting to the MAL API (required if mangaki_source_has_mal is
# enabled).
mangaki_source_mal_password: 'cheerio'

#################################
# Sentry integration (optional) #
#################################

# Whether to enable Sentry integration.
mangaki_source_has_sentry: true

# Sentry's DSN (required if Sentry integration is enabled)
mangaki_source_sentry_dsn: 'http://something@sentry.io/12390123'
```
