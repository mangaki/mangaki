This role configures a Redis store.

# Role variables

This role accepts the following parameters:

```yaml
# The amount of databases that Redis will run.
redis_databases: 1

# The network interfaces on which Redis will listen.
redis_bind: ['127.0.0.1']

# The port on which the Redis TCP socket will listen.
redis_port: 6379

# Set the Redis' store password to this value. If not provided, no password will be set.
redis_password: 'madscientist'

# Set the Redis' disk storage directory to this value.
redis_data_directory: '/var/lib/redis'
```

# Role handlers

This role exposes the following handlers:

- Restart redis.
