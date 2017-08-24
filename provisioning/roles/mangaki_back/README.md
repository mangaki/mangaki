# Mangaki backend role

This role configures a server for running Mangaki backend services:

- crons for top refresh.
- Celery workers.

## Dependencies

This role requires the Mangaki source code to be present and configured on the
server; as such, it should always be used in conjunction with the
[`mangaki_source` role](../mangaki_source/README.md) .

## Role variables

```
# Start Celery through supervisord (disabled in development, default: true)
start_celery: true
```
