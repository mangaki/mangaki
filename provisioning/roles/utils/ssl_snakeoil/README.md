This site role sets up a snakeoil SSL certificate for a domain.

# Role variables
Thie role accepts the following parameters:

```yaml
# The domain name for which SSL certificates should be generated. The
# certificate will be put in `/etc/ssl/certs/$snakeoil_domain.pem` and
# `/etc/ssl/certs/$snakeoil_domain.chained.pem`, while the private key will be in
# `/etc/ssl/private/$snakeoil_domain.key`.
snakeoil_domain: 'mangaki.fr'
```

# Handlers
This role does not expose any handler.
