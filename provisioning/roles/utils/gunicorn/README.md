# Gunicorn role

Configures this host to run a website through Gunicorn under supervisord.

## Role variables

```yaml
# User that should run the gunicorn service (required)
gunicorn_user: 'mangaki'

# Name of the supervised program (required)
gunicorn_program: 'mangaki'

# WSGI module to run (required)
gunicorn_wsgi: 'mangaki.wsgi:application'

# Virtualenv under which gunicorn should be run (required)
gunicorn_venv_path: '/home/mangaki/venv'

# Additional environment for the gunicorn program, as a dictionary
gunicorn_env: {}
```
