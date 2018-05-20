This site role setups a single nginx site.

# Role variables
This role accepts the following parameters:

```yaml
# Name for the nginx site. Must be unique.
nginx_site_name: 'default'

# Whether the site should be enabled
nginx_site_enabled: true

# Whether the site should be set up for ACME http challenges. If true,
# challenges will be served from the `nginx_site_acme_wellknown` directory.
nginx_site_use_acme: false

# Directory from which ACME challenges are to be served. This directory must
# already exist and will not be created by this role (required if
# nginx_site_use_acme is enabled).
nginx_site_acme_wellknown: '/var/www/acme-challenge/'

# Path to the root directory from which files should be served.
nginx_site_root: '/var/www/html'

# Domains from which the site should be served (required). The first domain is
# considered to be the main one, and other aliases for it.  The SSL certificate
# used for the site will be the ones configured for the main domain; they should
# be also valid for the aliases to prevent errors.
nginx_site_domains: ['mangaki.fr']

# Upstreams that the site should redirect to (required). They will be tried in
# order. Each upstream definition should be a dict with the following
# parameters:
#  - name: The name of the upstream
#  - servers: A list of URLs to which the request should be proxied; e.g.
#    127.0.0.1:8000 to redirect to a default gunicorn server.
nginx_site_upstreams:
  - name: 'mangaki'
    servers: ['127.0.0.1:8000']

# X-SendFile internal locations, tried in order.
# Each internal location definition should be a dict with the following parameters:
#  - path: The URI for NGINX, e.g. "/protected/"
#  - root: The disk path where files are which must be internal

nginx_site_xsendfile_internal_locations:
  - path: '/protected/'
    root: '/var/www/staticfiles/'
```

# Role handlers
This role exposes the same handlers as the [`utils/nginx` role](../nginx/README.md).
