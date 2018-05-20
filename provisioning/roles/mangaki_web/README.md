# Mangaki webserver

This role configures a server to serve Mangaki through nginx.

## Dependencies

This role doesn't have any dependencies and can be used in a standalone way on
any server.

# Role variables

This role accepts the following parameters:

```yaml
# Name to use for nginx's site
mangaki_web_name: 'mangaki'

# Whether to use Let's Encrypt SSL certificates
mangaki_web_use_acme: true

# Path to store ACME challenges
mangaki_web_acme_wellknown_path: '/var/www/acme-challenge/'

# ACME certificate authority to use
mangaki_web_acme_ca: 'https://acme-staging.api.letsencrypt.org/directory'

# ACME certificate authority terms
mangaki_web_acme_ca_terms: 'https://acme-staging.api.letsencrypt.org/terms'

# Root of the Mangaki website for serving static file (required). This is the
# *root* of the website; `favicon.ico` should be stored directly there, and
# Django static files should be put in a `static/` subdirectory. This makes it
# easy to add additional static pages to Mangaki by simply placing them there, as
# this directory will be tried prior to calling Mangaki's app servers.
mangaki_web_www_root: '/var/www/mangaki/'

# List of domains to serve from this installation of Mangaki (required). The
# first domain in the list is considered to be the canonical one, and every
# subsequent domains will redirect to the first.
mangaki_web_domains: ['mangaki.fr', 'www.mangaki.fr']

# NGINX specific — advanced
# X-SendFile path, this is the URI which will be internal but can be used by the web server.
mangaki_web_xsendfile_path: '/protected/'
# X-SendFile root, this is where NGINX is going to read files by concatenating the root and the path.
mangaki_web_xsendfile_root: '/var/www/mangaki'
# For example, sending the file /protected/secret.gif will make NGINX send the file /var/www/mangaki/protected/secret.gif ; meanwhile no one can access to /protected/secret.gif using a web browser.

```
