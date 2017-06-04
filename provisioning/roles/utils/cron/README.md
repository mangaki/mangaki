# Role for cron tasks

This role sets up a task that should execute regularly on the host.

*Note: even though this role is called after the Unix cron daemon, it actually
uses systemd timers.*

## Role variables

```yaml
# Name for this task's service and timer (required)
cron_name: 'mangaki-collectstatic'

# Description for this task's service (required)
cron_description: "Collect Mangaki's static files"

# Description for this task's timer.
cron_timer_description: "Timer for Collect Mangaki's static files"

# Whether this cron task should be marked for periodic runs.
cron_enabled: true

# The command to run (required).
cron_command: 'python manage.py collectstatic'

# The Unix username under which the command should be run (required).
cron_user: 'mangaki'

# The Unix group under which the command should be run
cron_group: 'mangaki'

# How often this cron should run, under systemd's OnCalendar format.
cron_schedule: 'daily'
```
