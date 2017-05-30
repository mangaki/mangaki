This site role configures a PostgreSQL database.

# Role variables

This role accepts the following parameters:

```yaml
# The name of the database that should be set up (required).
postgresql_database: 'mangaki'

# List of extensions that should be installed on the database.
postgresql_extensions: []

# Name of the user that should be granted access to the database (required).
postgresql_user: 'mangaki'

# Set the user's password to this value. If not provided, any existing password
will be kept -- use `null` to remove an existing password.
postgresql_password: 'tuturuu'
```

# Role handlers
This role does not provide any handler.
