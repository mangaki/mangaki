# Mangaki synchronization

This role runs maintenance tasks (such as migrating the database and collecting
static files) on a single server.

## Dependencies

This role requires the Mangaki source code to be present and configured on the
server; as such, it should always be used in conjunction with the
[`mangaki_source` role](../mangaki_source/README.md).

# Role variables

This role accepts the following parameters:

```yaml
# Perform database migration
mangaki_sync_migrate: true

# Collect static files
mangaki_sync_collectstatic: true

# Load the seed
mangaki_sync_load_seed: false

# Path to the seed to load on the host (required if `mangaki_sync_load_seed` is
# enabled.)
mangaki_sync_load_seed_path: 'seed_data.json'
```
