# Nix-based setup in Mangaki

Mangaki uses Nix Flakes to manage:

- development shell ;
- development setup ;
- VM setup ;
- running end to end tests in VM ;
- production setup

Ensure you have a fairly recent Nix (> 2.0) and Flakes enabled.

You can allow the `.envrc` with `direnv` or use `nix-shell` directly.

### Database setup

Ensure you have a PostgreSQL running: `services.postgresql.enable = true;` might be enough if you are using NixOS.

Create a user the same as in the default installation.

### Running the web server

`$ django-admin runserver` is enough.

**Warning** : Sometimes, you can run into a shell confusion bug where it tries to run Python on a Bash wrapped file, in that case, use `python manage.py runserver` and do not rely on `django-admin`. This is a known bug.

### Running background tasks (Celery)

This requires Redis to be running: `services.redis.enable = true;` does the job.

`$ celery worker -B -A mangaki:celery_app -l INFO` is enough.

### For maintainers and updating Poetry lockfiles

To relock overrides, you can run `poetry2nix lock` to update `overrides.nix` (in particular: Mangaki Zero).

When adding a dependency with Poetry while using Nix, you may want to do `poetry add xxx --lock` to perform only the lock computations.

**Note** : Poetry has some versions where the lockfile produced is broken, check with upstream bugs at that moment.

### QEMU install

Just run `nix-build -A nixosConfigurations.vm.config.system.build.vm` and `result/bin/run-nixos-vm`, enjoy Mangaki on <https://localhost:8000> in the virtual machine.

**Note** : The state is stored in a local disk ending by `qcow2`, deleting it would reset the VM.
