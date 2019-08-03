Mangaki
=======

[![Dependency Status](https://dependencyci.com/github/mangaki/mangaki/badge)](https://dependencyci.com/github/mangaki/mangaki)
[![CircleCI](https://circleci.com/gh/mangaki/mangaki.svg?style=svg)](https://circleci.com/gh/mangaki/mangaki)
[![Codecov](https://img.shields.io/codecov/c/github/mangaki/mangaki.svg)]()

Je suis le manuel d'installation de Mangaki. Vous ne pouvez pas savoir comme ça me fait plaisir que vous me lisiez !

Mangaki est [sous licence AGPLv3](https://en.wikipedia.org/wiki/Affero_General_Public_License).


Comment contribuer ?
--------------------

Que vous soyez simple otaku, data expert, codeur Python, passionné d'algo, data scientist ou designer, vous pouvez contribuer à Mangaki ! Quelques pistes sont sur le [wiki](https://github.com/mangaki/mangaki/wiki), mais aussi dans le fichier [CONTRIBUTING.md](./CONTRIBUTING.md) !


Prérequis
---------

- 3.4 ≤ Python ≥ 3.6
- 9.3 ≤ PostgreSQL ≤ 10
- 4.0.0 ≤ Redis ≤ 4.0.2

Si vous n'avez jamais fait de Django, je vous renvoie vers [leur super tutoriel](https://docs.djangoproject.com/en/1.9/intro/tutorial01/).


Configurer PostgreSQL
---------------------

Vous allez avoir besoin d'un utilisateur qui a accès à la base de données. La
façon la plus simple de faire ça est simplement de créer un compte qui a le
même nom que votre nom d'utilisateur, qui peut créer des bases de données, et
qui est un super-utilisateur (pour CREATE EXTENSION) :

    sudo -u postgres createuser --superuser --createdb $USER

Vous aurez besoin de l'utilitaire `pwgen` pour générer un mot de passe
aléatoire lors de la configuration.

Ensuite, vous pouvez créer la base de données et ajouter les extensions
requises :

    createdb mangaki
    psql -d mangaki -c \
        "create extension if not exists pg_trgm; \
         create extension if not exists unaccent"


Lancer un serveur de développement
----------------------------------

Premièrement, copiez la configuration. Les paramètres par défaut sont censés
marcher, donc vous ne devriez pas avoir besoin de changer quoi que ce soit :

    cp mangaki/settings{.template,}.ini

Ensuite, vous pouvez installer l'environnement de Django :

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements/dev.txt
    ./mangaki/manage.py migrate
    ./mangaki/manage.py runserver

Si vous souhaitez mettre en production une instance de Mangaki, le fichier de
configuration est un peu plus complexe - regardez dans `settings.template.ini`
et `mangaki/settings.py` pour un aperçu des options utiles.


Remplir la base de données
--------------------------
    
    cd mangaki
    ./manage.py migrate
    ./manage.py loaddata ../fixtures/{partners,seed_data}.json
    ./manage.py ranking # Compute cached ranking information. This should be done regularly.
    ./manage.py top --all # Store data for the Top20 page. This should be done regularly.

Voilà ! Vous avez une installation de Mangaki fonctionnelle.


Lancer les tests
----------------

    . venv/bin/activate
    ./mangaki/manage.py test

Ceci va lancer les [doctests](https://docs.python.org/3.5/library/doctest.html) et les tests unitaires contenus dans chaque application avec un dossier `tests`.

Pour calculer la couverture de test, il faut plutôt faire:

    coverage run ./mangaki/manage.py test --with-coverage --cover-package=mangaki,irl --cover-html

Ainsi, vous aurez un dossier `cover` qui contiendra les informations de couverture en HTML.


Installation facile (Vagrant)
-----------------------------

Vous devez installer [Vagrant](https://www.vagrantup.com/downloads.html).

    vagrant up
    vagrant ssh
    ./manage.py runserver 0.0.0.0:8000

Votre machine virtuelle est maintenant prête.
Vous pouvez utiliser Mangaki à l'adresse `app.mangaki.dev:8000` (si vous avez le plugin `vagrant-hostsupdater`) ou `192.168.33.10:8000`.

Pour plus de détails, lisez le script `provisioning/bootstrap.sh` qui s'occupe de mettre en place la machine.

:warning: **Attention** :warning: : L'installation vous prendra environ _3 Gio_, une fois terminée. C'est en raison principalement de l'image Debian qui est téléchargée puis installée dans la machine virtuelle.


Remarques utiles
----------------

Si vous vous rendez sur la page des mangas, la troisième colonne chargera en boucle. C'est parce que le Top Manga est vide, pour des raisons intrinsèques à [`ranking.py`](https://github.com/mangaki/mangaki/blob/master/mangaki/mangaki/management/commands/ranking.py#L9).

Si vous obtenez des erreurs 400 lorsque vous mettez Mangaki en production (c'est-à-dire que `DEBUG = False`), faites bien attention à modifier les `ALLOWED_HOSTS` qui se trouvent dans votre configuration (`mangaki/settings/`) afin d'autoriser votre [FQDN](https://fr.wikipedia.org/wiki/Fully_qualified_domain_name) dedans.

Pour une mise en production, veillez à faire `./manage.py collectstatic` afin d'obtenir les assets: il est possible de changer le repertoire dans `mangaki/settings.py` (la variable `STATIC_ROOT`).

Mangaki a été testé et fonctionne parfaitement avec NGINX et Gunicorn.


Nous contacter
--------------

En cas de pépin, [créez un ticket](https://github.com/mangaki/mangaki/issues) ou contactez-moi à vie@jill-jenn.net.
