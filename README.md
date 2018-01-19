# Mangaki

[![Dependency Status](https://dependencyci.com/github/mangaki/mangaki/badge)](https://dependencyci.com/github/mangaki/mangaki)
[![CircleCI](https://circleci.com/gh/mangaki/mangaki.svg?style=svg)](https://circleci.com/gh/mangaki/mangaki)
[![Codecov](https://img.shields.io/codecov/c/github/mangaki/mangaki.svg)](https://codecov.io/gh/mangaki/mangaki/)

Here is Mangaki's installation manual. Welcome!  
Also available [in French](README-fr.md).

## Install

### VM install (super simple but requires 6 GB)

Requires [Vagrant](https://www.vagrantup.com/downloads.html).

    vagrant up
    vagrant provision  # May be required
    vagrant ssh  # Will open a tmux that
    # You can detach by pressing Ctrl + b then d

And voilà! You can access Mangaki at http://192.168.33.10:8000 (or http://app.mangaki.dev if you have `vagrant-hostupdater`).

### Full install

Requires Python 3.4 → 3.6, PostgreSQL 9.3 → 10, Redis 4.0, and preferably `pwgen`.

    ./config.sh
    python3 -m venv venv
    . venv/bin/activate
    pip install -r requirements/dev.txt
    cd mangaki
    ./manage.py migrate

#### Running the background worker (Celery)

This step is mandatory only if you need background tasks which is required for features such as MAL imports.

     # Ensure that your working directory is where manage.py is. (i.e. ls in this folder should show you manage.py)
     celery -B -A mangaki:celery_app worker -l INFO

If you can read something along these lines:

```console
[2017-10-29 14:34:47,810: INFO/MainProcess] celery@your_hostname ready.
```

The worker is ready to receive background tasks (e.g. MAL imports).

#### Running the web server

    ./manage.py runserver

And voilà! You can access Mangaki at http://localhost:8000.

## Some perks

    ./manage.py loaddata ../fixtures/{partners,seed_data}.json
    ./manage.py ranking    # Compute the anime/manga ranking pages. Should be done regularly.
    ./manage.py top --all  # Compute the Top 20 directors, etc. Should be done regularly.
    ./manage.py test       # Run all tests

See also our interesting [Jupyter notebooks](https://github.com/mangaki/notebooks), in another repository.

## Contribute

- Read [CONTRIBUTING.md](CONTRIBUTING.md)
- Browse the [issues](https://github.com/mangaki/mangaki/issues) and the [wiki](https://github.com/mangaki/mangaki/wiki)
- First time? Track the [`good first issue`](https://github.com/mangaki/mangaki/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) label!

## Contact

- Feel free to contact us at jj@mangaki.fr
- Found a bug? [Create an issue](https://github.com/mangaki/mangaki/issues/new).
- Stay in touch with our blog: http://research.mangaki.fr
