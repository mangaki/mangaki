Mangaki
=======

[![Dependency Status](https://dependencyci.com/github/mangaki/mangaki/badge)](https://dependencyci.com/github/mangaki/mangaki)

Voici le manuel d'installation de Mangaki. Vous ne pouvez pas savoir comme ça fait plaisir que vous me lisiez !

Mangaki est [sous licence AGPLv3](https://en.wikipedia.org/wiki/Affero_General_Public_License).

Comment contribuer ?
--------------------

Que vous soyez simple otaku, data expert, codeur Python, passionné d'algo, data scientist ou designer, vous pouvez contribuer à Mangaki ! Quelques pistes sont sur le [wiki](https://github.com/mangaki/mangaki/wiki), mais aussi dans le fichier [CONTRIBUTING.md](./CONTRIBUTING.md) !

Prérequis
---------

- Python 3.4
- virtualenv
- PostgreSQL ≥ 9.3 (9.4.2 étant mieux)
* `python3-sqlparse` pour la Debug Toolbar (**inutile** en production).

Si vous n'avez jamais fait de Django, je vous renvoie vers [leur super tutoriel](https://docs.djangoproject.com/en/1.9/intro/tutorial01/).

Configurer PostgreSQL
---------------------

Vous aurez besoin de l'utilitaire `pwgen` pour générer un mot de passe
aléatoire lors de la configuration.

    sudo -u postgres -H createdb mangaki
    sudo -u postgres -H createuser django
    export DB_PASSWORD=$(pwgen -s -c 30 1)
    sudo -u postgres -H DB_PASSWORD=$DB_PASSWORD psql -d mangaki -c \
      "alter user django with password '$DB_PASSWORD'; \
      grant all privileges on database mangaki to django; \
      create extension if not exists pg_trgm; \
      create extension if not exists unaccent"

Configurer un environnement virtuel
-----------------------------------

Il est fortement recommandé d'installer les dépendances de Mangaki dans un
environnement virtuel, ce qui est fait par les commandes ci-dessous.
    
    python3 -m venv venv --system-site-packages
    . venv/bin/activate
    pip install -r requirements.txt
    pip install -r requirements-dev.txt # Si installation d'une instance de développement

Pour activer l'environnement virtuel dans le futur, il faudra faire

    . venv/bin/activate

Configurer Mangaki
------------------

Pour configurer Mangaki, il faut créer un fichier `settings.ini` à la racine de
l'application. Pour une installation de développement, il suffit de faire :

    cat > mangaki/settings.ini <<EOF
    [debug]
    DEBUG = True

    [secrets]
    SECRET_KEY = $(pwgen -s -c 60 1)
    DB_PASSWORD = ${DB_PASSWORD}

    [email]
    EMAIL_BACKEND = django.core.mail.backends.console.EmailBackend
    EOF

Si vous souhaitez mettre en production une instance de Mangaki, le fichier de
configuration est un peu plus complexe - regardez dans `mangaki/settings.py`
pour un aperçu des options utiles.

Remplir la base de données
--------------------------
    
    cd mangaki
    ./manage.py migrate
    ./manage.py loaddata ../fixtures/{partners,seed_data}.json
    ./manage.py ranking # Compute cached ranking information. This should be done regularly.
    ./manage.py top director # Store data for the Top20 page. This should be done regularly.

Voilà ! Vous avez une installation de Mangaki fonctionnelle.

Afficher les notebooks
----------------------

    . venv/bin/activate
    pip install ipython[notebook]

Ensuite, vous pourrez faire `./mangaki/manage.py shell_plus --notebook` pour lancer IPython Notebook. Les notebooks se trouvent… dans le dossier `notebook`.


Lancer les tests
----------------

    . venv/bin/activate
    ./mangaki/manage.py test

Ceci va lancer les [doctests](https://docs.python.org/3.5/library/doctest.html) et les tests unitaires contenus dans chaque application avec un dossier `tests`.

Pour calculer la couverture de test, il faut plutôt faire:

    coverage run ./mangaki/manage.py test --with-coverage --cover-package=mangaki,irl,discourse --cover-html

Ainsi, vous aurez un dossier `cover` qui contiendra les informations de couverture en HTML.

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
