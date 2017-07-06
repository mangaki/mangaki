# Mangaki backend role

This role configures a server for running Mangaki backend services. For now,
those "services" are limited to a couple of cron tasks; in the future they may
become more complex with and be replaced e.g. with a Celery setup.

## Dependencies

This role requires the Mangaki source code to be present and configured on the
server; as such, it should always be used in conjunction with the
[`mangaki_source` role](../mangaki_source/README.md) .

## Role variables

This role does not define any specific parameters; it infers all its
configuration from its dependent roles.
