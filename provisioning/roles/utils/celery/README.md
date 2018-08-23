# Celery role

Configures this host to run Celery workers under supervisord.

## Role variables

```yaml
# Name of the supervisor application (required)
celery_name: 'mangaki_celery'

# User that should run the Celery workers (required)
celery_user: 'mangaki'

# Celery application module (required)
celery_app_module: 'mangaki'

# Celery application name (required)
celery_app_name: 'celery_app'

# Virtualenv under which Celery should run (required)
celery_venv_path: '/home/mangaki/venv'

# Celery log level
celery_log_level: 'INFO'

# Celery autoscale (min / max concurrency)
celery_autoscale_min: 3
celery_autoscale_max: 10

# Additional environment for the Celery program, as a dictionary
celery_env: {}

# Enable the beat scheduler
celery_beat: true

# Start Celery through supervisorctl (default: true)
start: true
```
