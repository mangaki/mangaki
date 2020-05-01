.. role:: raw-html-m2r(raw)
   :format: html


Mangaki
=======


.. image:: https://circleci.com/gh/mangaki/mangaki.svg?style=svg
   :target: https://circleci.com/gh/mangaki/mangaki
   :alt: CircleCI


.. image:: https://img.shields.io/codecov/c/github/mangaki/mangaki.svg
   :target: https://codecov.io/gh/mangaki/mangaki/
   :alt: Codecov


Welcome to Mangaki!\ :raw-html-m2r:`<br>`
This README is also available `in French <README-fr.md>`_.

What to do from here?
---------------------

AI for Manga & Anime
^^^^^^^^^^^^^^^^^^^^


.. image:: http://research.mangaki.fr/public/img/aima/aima-banner.png
   :target: http://research.mangaki.fr/public/img/aima/aima-banner.png
   :alt: AI for Manga & Anime


`Read about our keynote <http://research.mangaki.fr/2018/07/15/ai-for-manga-and-anime/>`_ at Anime Expo, Los Angeles in July 2018.

Mangaki on Earth (MoE): visualizing anime embeddings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


.. image:: http://research.mangaki.fr/public/img/embeddings.png
   :target: http://research.mangaki.fr/public/img/embeddings.png
   :alt: Visualize anime embeddings



* See `our blog post <http://research.mangaki.fr/2018/08/23/mangaki-on-earth-visualize-anime-embeddings/>`_
* Our map `Mangaki on Earth <https://mangaki.fr/map>`_
* Browse `other interesting notebooks <https://github.com/mangaki/notebooks>`_.

Install Mangaki
---------------

Database setup
^^^^^^^^^^^^^^

You need to have PostgreSQL >9.3 running on your machine. You also need an
user that will have access to the database. The easiest way to achieve that is
simply to create an account which has the same name as your username, which
can create databases, and which is a superuser (for CREATE EXTENSION):

.. code-block::

   sudo -u postgres createuser --superuser --createdb $USER


Then create the database, and add the required extensions:

.. code-block::

   createdb mangaki
   psql -d mangaki -c \
       "create extension if not exists pg_trgm; \
        create extension if not exists unaccent"


Running the web server
^^^^^^^^^^^^^^^^^^^^^^

First, copy the configuration. The default parameters are already supposed to
work, so you shouldn't need to change anything:

.. code-block::

   cp mangaki/settings{.template,}.ini


You can then install the Django environment:

.. code-block::

   poetry install
   poetry shell
   ./mangaki/manage.py migrate
   ./mangaki/manage.py runserver


And voilà! You can access Mangaki at http://localhost:8000.

Running background tasks (Celery)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Background tasks represent:


* importing anime from another database;
* looking for duplicates in the database;
* (in a near future) improve Mangaki models.

These are optional, but if you want to try them:

.. code-block::

    # Ensure that your working directory contains manage.py
    celery -B -A mangaki:celery_app worker -l INFO


If you can read something like this:

.. code-block:: console

   [2018-08-23 13:37:42,000: INFO/MainProcess] celery@your_hostname ready.

The worker is ready to receive background tasks (e.g. MAL imports).

VM install
^^^^^^^^^^

You can also `install Mangaki in a VM <https://github.com/mangaki/mangaki/wiki/How-to-install-Mangaki-using-a-virtual-machine-(simple-but-takes-2-GB>`_\ ) using our amazing Ansible playbooks.

It's simple but takes 2 GB.

Populate the database with a few fixtures
-----------------------------------------

The database starts empty, but you can populate a few works:

.. code-block::

   ./manage.py loaddata ../fixtures/{partners,seed_data}.json
   ./manage.py ranking    # Compute the anime/manga ranking pages. Should be done regularly.
   ./manage.py top --all  # Compute the Top 20 directors, etc. Should be done regularly.
   ./manage.py test       # Run all tests


See also our interesting `Jupyter notebooks <https://github.com/mangaki/notebooks>`_\ , in another repository.

Contribute
----------


* Read `CONTRIBUTING.md <CONTRIBUTING.md>`_
* Browse the `issues <https://github.com/mangaki/mangaki/issues>`_ and the `wiki <https://github.com/mangaki/mangaki/wiki>`_
* First time? Track the `\ ``good first issue`` <https://github.com/mangaki/mangaki/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22>`_ label!

Contact
-------


* Feel free to contact us at jj@mangaki.fr
* Found a bug? `Create an issue <https://github.com/mangaki/mangaki/issues/new>`_.
* Stay in touch with our blog: http://research.mangaki.fr
