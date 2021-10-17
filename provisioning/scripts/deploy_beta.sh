#!/usr/bin/env bash

# Assumptions:
# - You're currently in somewhere/mangaki_repository/
# - You're already under some virtual env which can execute setup.py sdist.

SITE_YAML="provisioning/site.yml"
BETA_INVENTORY_HOSTS="provisioning/inventories/staging/hosts"
BETA_PASSWORD_FILE_PATH="$(pwd)/.vault_pass.txt"

# Sanity checks.
if [ -z "$BETA_VAULT_PASSWORD" ]
then
        echo "BETA_VAULT_PASSWORD environment variable is not set. Cannot continue."
        exit 1
fi

# Get a hang of where are we.
# Prepare a nice package.
# TODO: poetry build -f sdist — when we stabilize versioning.
cd mangaki && python setup.py sdist && cd ..
# Get the path to the package.
LOCAL_PACKAGE_NAME=$(find "mangaki/dist" -maxdepth 1 -name "*.tar.gz" | xargs ls -t | head -n1)
LOCAL_PACKAGE_PATH="$(pwd)/$LOCAL_PACKAGE_NAME"
echo "I will install $LOCAL_PACKAGE_PATH on beta.mangaki.fr."
# Prepare the password file.
touch ~/.vault_pass.txt
chmod 600 ~/.vault_pass.txt
# Put the password in a file for Ansible Vault.
echo "$BETA_VAULT_PASSWORD" > "$BETA_PASSWORD_FILE_PATH"
echo "Password inserted."
# Run the playbook.
ansible-playbook $SITE_YAML \
        -e mangaki_sync_compilemessages=true \
        -e mangaki_sync_collectstatic=true \
        -e mangaki_sync_migrate=true \
        -e mangaki_source_package_local="$LOCAL_PACKAGE_PATH" \
        -i "$BETA_INVENTORY_HOSTS" \
        --vault-password-file "$BETA_PASSWORD_FILE_PATH"
ANSIBLE_STATUS=$?

# Clean up the evidence.
rm "$BETA_PASSWORD_FILE_PATH"
echo "Password deleted."

# Inform the CI in case of problems.
if [ $ANSIBLE_STATUS -ne 0 ]
then
        echo "Failed to provision beta. Failing the test."
        exit 1
fi
