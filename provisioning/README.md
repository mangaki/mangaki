# Mangaki deployment with Ansible

## Inventories

We currently provide a single inventory, `staging`, that replicates the one we
use for syncing the `beta.mangaki.fr` instance. You should use different inventories for each of your deployments.

Sensible defaults for most configuration options should be automatically
inferred from a few variables; please refer to
[here](inventories/staging/host_vars/beta.mangaki.fr/vars) for an example
configuration (note that you should create an Ansible Vault at `/vault` in
order to configure the secret `vault_*` variables present in that file).

## HTTPS and other troubles

Don't forget to update your DNS records so that they point to the right IP
address before attempting deployment, or the Let's Encrypt setup will fail.
