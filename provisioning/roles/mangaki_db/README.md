# Mangaki database

This role configures a server for acting as a Mangaki database server; which
means it simply configures a PostgreSQL server according to the Mangaki site
configuration.

## Dependencies

This role doesn't have any dependencies and can be used in a standalone way on
any server.

## Role variables

This role accepts the following parameters:

```yaml
# Name of the database that should be created
mangaki_db_name: 'mangaki'

# Name of the user that should be granted access to the database
mangaki_db_user: 'mangaki'

# Password for accessing the database (required).
mangaki_db_password: 'tuturuu'

# When enabled, save the database into `mangaki_db_dump_path_local`. Mutually
# exclusive with `mangaki_db_load`.
mangaki_db_dump: false

# When enabled, load the database from an existing dump at
# `mangaki_db_dump_path_local`. Mutually exclusive with `mangaki_db_dump`.
mangaki_db_load: false

# Path on the coordinator for the database dump (see `mangaki_db_dump` and
# `mangaki_db_load` for details); required if either `mangaki_db_dump` or
# `mangaki_db_load` is enabled.
mangaki_db_dump_path_local: mangaki.pgdump
```
