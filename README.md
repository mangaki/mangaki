Mangaki
=======

Voici le manuel d'installation de Mangaki. Vous ne pouvez pas savoir comme ça fait plaisir que vous me lisiez !

Mangaki est [sous licence AGPLv3](https://en.wikipedia.org/wiki/Affero_General_Public_License).

Comment contribuer ?
--------------------

Que vous soyez simple otaku, data expert, codeur Python, passionné d'algo, data scientist ou designer, vous pouvez contribuer à Mangaki ! Quelques pistes sont sur le [wiki](https://github.com/mangaki/mangaki/wiki).

Prérequis
---------

- Python 3.4
- virtualenv
- PostgreSQL ≥ 9.3 (9.4.2 étant mieux)
* `python3-lxml` (autrement, vous pouvez [l'installer par pip](http://stackoverflow.com/questions/6504810/how-to-install-lxml-on-ubuntu) aussi)
* `python3-sqlparse` pour la Debug Toolbar (**inutile** en production).

Si vous n'avez jamais fait de Django, je vous renvoie vers [leur super tutoriel](https://docs.djangoproject.com/en/1.8/intro/tutorial01/).

Configurer PostgreSQL
---------------------

    createuser django
    createdb mangaki
    psql mangaki
    # alter user django with password 'XXX';
    # grant all privileges on database mangaki to django;
    # create extension if not exists pg_trgm;
    # create extension if not exists unaccent;

Lancer le serveur
-----------------

    python3 -m venv venv
    . venv/bin/activate
    pip install -r requirements.txt
    cd mangaki
    cp secret_template.py secret.py  # À modifier, notamment le mot de passe d'accès à la base de données
    echo "from .dev import *" > mangaki/settings/__init__.py # À ajuster, selon votre cas (production) avec DJANGO_SETTINGS_MODULE si nécessaire.
    ./manage.py migrate
    ./manage.py loaddata ../fixtures/{partners,ghibli,kizu,seed_data}.json
    ./manage.py ranking # Compute cached ranking information. This should be done regularly.
    ./manage.py top director # Store data for the Top20 page. This should be done regularly.
    ./manage.py runserver

Afficher les notebooks
----------------------

    . venv/bin/activate
    pip install ipython[notebook]
    pip install django-extensions

Ensuite, vous pourrez faire `./mangaki/manage.py shell_plus --notebook` pour lancer IPython Notebook. Les notebooks se trouvent… dans le dossier `notebook`.

Installation facile (Vagrant)
-----------------------------

Vous devez installer [Vagrant](https://www.vagrantup.com/downloads.html), puis installer les dépendances de rôles avec [ansible-galaxy](http://docs.ansible.com/ansible/galaxy.html):

    vagrant up
    vagrant ssh
    cd /mnt/mangaki
    . .venv/bin/activate
    cd mangaki
    ./manage.py runserver 0.0.0.0:8000

Votre machine virtuelle tourne sous Trusty64, le repo est monté via un shared folder sur `/mnt/mangaki`.
Il y a un virtualenv dans `/mnt/mangaki/.venv`, et le serveur devrait être lancé sur `0.0.0.0:8000`.
Enfin, vous pouvez contacter votre version locale de Mangaki à travers `192.168.42.10:8000` et `127.0.0.1:8080` (port forwarded).


Remarques utiles
----------------

Si vous vous rendez sur la page des mangas, la troisième colonne chargera en boucle. C'est parce que le Top Manga est vide, pour des raisons intrinsèques à [`ranking.py`](https://github.com/mangaki/mangaki/blob/master/mangaki/mangaki/management/commands/ranking.py#L9).

Lors d'une mise en production, il est plus sage d'écrire `from .prod import *` dans le fichier `mangaki/settings/__init__.py` avant de lancer votre conteneur WSGI.

Si vous obtenez des erreurs 400 lorsque vous mettez Mangaki en production (c'est-à-dire que `DEBUG = False`), faites bien attention à modifier les `ALLOWED_HOSTS` qui se trouvent dans votre configuration (`mangaki/settings/`) afin d'autoriser votre [FQDN](https://fr.wikipedia.org/wiki/Fully_qualified_domain_name) dedans.

Pour une mise en production, veillez à faire `./manage.py collectstatic` afin d'obtenir les assets: il est possible de changer le repertoire dans `mangaki/settings.py` (la variable `STATIC_ROOT`).

Mangaki a été testé et fonctionne parfaitement avec NGINX et Gunicorn.

Nous contacter
--------------

En cas de pépin, [créez un ticket](https://github.com/mangaki/mangaki/issues) ou contactez-moi à vie@jill-jenn.net.
