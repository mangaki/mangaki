# Mangaki

[![Dependency Status](https://dependencyci.com/github/mangaki/mangaki/badge)](https://dependencyci.com/github/mangaki/mangaki)
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

### Running the web server

Requires Python 3.4 up to 3.6, PostgreSQL 9.3 up to 10, Redis 4.0, and preferably `pwgen`.

    ./config.sh
    python3 -m venv venv
    . venv/bin/activate
    pip install -r requirements/dev.txt
    cd mangaki
    ./manage.py migrate
    ./manage.py runserver

And voilà! You can access Mangaki at http://localhost:8000.

### Running background tasks (Celery)

Background tasks represent:

- importing anime from another database;
- looking for duplicates in the database;
- (in a near future) improve Mangaki models.

These are optional, but if you want to try them:

     # Ensure that your working directory contains manage.py
     celery -B -A mangaki:celery_app worker -l INFO

If you can read something like this:

```console
[2018-08-23 13:37:42,000: INFO/MainProcess] celery@your_hostname ready.
```

The worker is ready to receive background tasks (e.g. MAL imports).

### VM install

You can also [install Mangaki in a VM](https://github.com/mangaki/mangaki/wiki/How-to-install-Mangaki-using-a-virtual-machine-(simple-but-takes-2-GB)) using our amazing Ansible playbooks.

It's simple but takes 2 GB.

## Populate the database with a few fixtures

The database starts empty, but you can populate a few works:

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
