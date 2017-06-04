# Mangaki frontend

This role configures a server for running the Mangaki frontend, which mostly
consists of a gunicorn setup monitored by supervisord.

## Dependencies

This role requires the Mangaki source code to be present and configured on the
server; as such, it should always be used in conjunction with the
[`mangaki_source` role](../mangaki_source/README.md).

## Role variables

This role does not define any specific parameters; it infers all its
configuration from its dependent roles.
