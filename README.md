# Mangaki

[![CircleCI](https://circleci.com/gh/mangaki/mangaki.svg?style=svg)](https://circleci.com/gh/mangaki/mangaki)
[![Codecov](https://img.shields.io/codecov/c/github/mangaki/mangaki.svg)](https://codecov.io/gh/mangaki/mangaki/)

Welcome to Mangaki!
This README is also available [in French](README-fr.md).

## What to do from here?

### AI for Manga & Anime

![AI for Manga & Anime](http://research.mangaki.fr/public/img/aima/aima-banner.png)

[Read about our keynote](http://research.mangaki.fr/2018/07/15/ai-for-manga-and-anime/) at Anime Expo, Los Angeles in July 2018.

### Mangaki on Earth (MoE): visualizing anime embeddings

![Visualize anime embeddings](http://research.mangaki.fr/public/img/embeddings.png)

- See [our blog post](http://research.mangaki.fr/2018/08/23/mangaki-on-earth-visualize-anime-embeddings/)
- Our map [Mangaki on Earth](https://mangaki.fr/map)
- Browse [other interesting notebooks](https://github.com/mangaki/notebooks).

## Install Mangaki

### Database setup

You need to have PostgreSQL >9.3 running on your machine. You also need an
user that will have access to the database. The easiest way to achieve that is
simply to create an account which has the same name as your username, which
can create databases, and which is a superuser (for CREATE EXTENSION):

    sudo -u postgres createuser --superuser --createdb $USER

Then create the database, and add the required extensions:

    createdb mangaki
    psql -d mangaki -c \
        "create extension if not exists pg_trgm; \
         create extension if not exists unaccent"

### Running the web server

You will need Python ≥ 3.7 and Poetry.

First, copy the configuration. The default parameters are already supposed to
work, so you shouldn't need to change anything:

    cp mangaki/settings{.template,}.ini

You can then install the Django environment:

    poetry install  # Add --no-dev if in production
    poetry shell
    ./mangaki/manage.py migrate
    ./mangaki/manage.py runserver  # If in dev; otherwise install gunicorn or anything by your own means

And voilà! You can access Mangaki at <http://localhost:8000>.

### Running background tasks (Celery)

Background tasks represent:

- importing anime from another database;
- looking for duplicates in the database;
- (in a near future) improve Mangaki models.

These are optional, but if you want to try them:

     # The PYTHONPATH hack is necessary. If you don't like it, read the Nix section.
     PYTHONPATH=$PYTHONPATH:`pwd`/mangaki celery -B -A mangaki:celery_app worker -l INFO

If you can read something like this:

```console
[2018-08-23 13:37:42,000: INFO/MainProcess] celery@your_hostname ready.
```

The worker is ready to receive background tasks (e.g. MAL imports).

## New: Nix-based installation

Ensure you have a fairly recent Nix (> 2.0) and have `direnv`.

Allow the `.envrc` to run.

### Database setup

### Running the web server

### Poetry maintainer version

If you use `direnv`, you will always have `poetry`, `poetry2nix` and `nixfmt` automagically installed in your shell.

Moreover, `DJANGO_SETTINGS_MODULE` & `PYTHONPATH` is automatically propagated.

Thus, you can replace `./managki/manage.py` by `django-admin` from wherever you are in your filesystem.

Also, you can drop the `PYTHONPATH` hack to run Celery, it will just work out of the box, from wherever you are in your filesystem again. :-)

### I don't want to figure out too much version

Just do `nix-shell -f default.nix -A wheeledShell`, enjoy `django-admin` and `celery` without any hack.

### I want to do something arbitrary complex

Please read the `default.nix` and add your use cases, you can run `nix-shell -f default.nix -A sourceShell` to recompile everything, including NumPy & SciPy, note that it's going to be a bit long.

### QEMU install

Just run `nix-build -A nixosConfigurations.vm.config.system.build.vm` and `result/bin/run-nixos-vm`, enjoy Mangaki on <https://localhost:8000>

### VM install

You can also [install Mangaki in a VM](https://github.com/mangaki/mangaki/wiki/How-to-install-Mangaki-using-a-virtual-machine-(simple-but-takes-2-GB)) using our amazing Ansible playbooks.

It's simple but takes 2 GB.

## Populate the database with a few fixtures

The database starts empty, but you can populate a few works:

    ./mangaki/manage.py loaddata ../fixtures/{partners,seed_data}.json
    ./mangaki/manage.py ranking    # Compute the anime/manga ranking pages. Should be done regularly.
    ./mangaki/manage.py top --all  # Compute the Top 20 directors, etc. Should be done regularly.
    py.test mangaki/               # Run all tests

See also our interesting [Jupyter notebooks](https://github.com/mangaki/notebooks), in another repository.

## Contribute

- Read [CONTRIBUTING.md](CONTRIBUTING.md)
- Browse the [issues](https://github.com/mangaki/mangaki/issues) and the [wiki](https://github.com/mangaki/mangaki/wiki)
- First time? Track the [`good first issue`](https://github.com/mangaki/mangaki/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) label!

## Contact

- Feel free to contact us at jj@mangaki.fr
- Found a bug? [Create an issue](https://github.com/mangaki/mangaki/issues/new).
- Stay in touch with our blog: http://research.mangaki.fr

## License information

Mangaki is an open-sourced project licensed under AGPLv3. For accurate information regarding license and copyrights, please check individual files. 

