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

Si vous n'avez jamais fait de Django, je vous renvoie vers [leur super tutoriel](https://docs.djangoproject.com/en/1.8/intro/tutorial01/).

Configurer PostgreSQL
---------------------

    createuser django
    createdb mangaki
    psql mangaki
    # alter user django with password 'XXX';
    # grant all privileges on database mangaki to django;

Lancer le serveur
-----------------

    python3 -m venv venv
    . venv/bin/activate
    pip install -r requirements.txt
    cd mangaki
    cp secret_template.py secret.py  # À modifier, notamment le mot de passe d'accès à la base de données
    ./manage.py migrate
    ./manage.py loaddata ../fixtures/seed_data.json
    ./manage.py runserver

Installation facile (Vagrant)
-----------------------------

Vous devez installer [Vagrant](https://www.vagrantup.com/downloads.html), puis installer les dépendences de rôles avec [ansible-galaxy](http://docs.ansible.com/ansible/galaxy.html):

    vagrant up
    vagrant ssh
    cd /mnt/mangaki
    . .venv/bin/activate
    cd mangaki
    ./manage.py runserver 0.0.0.0:8000

Votre machine virtuelle tourne sous Trusty64, le repo est monté via un shared folder sur `/mnt/mangaki`.
Il y a un virtualenv dans `/mnt/mangaki/.venv`, et le serveur devrait être lancé sur `0.0.0.0:8000`.
Enfin, vous pouvez contacter votre version locale de Mangaki à travers `192.168.42.10:8000` et `127.0.0.1:8080` (port forwaded).


Remarques utiles
----------------

Si vous vous rendez sur la page des mangas, la troisième colonne chargera en boucle. C'est parce que le Top Manga est vide, pour des raisons intrinsèques à [`ranking.py`](https://github.com/mangaki/mangaki/blob/master/mangaki/mangaki/management/commands/ranking.py#L9).

Si vous vous inscrivez, vous obtiendrez une erreur « Connection refused ». C'est normal, votre serveur de mails n'est pas installé. Pour éviter ce comportement temporairement, vous pouvez décommenter la ligne suivante de `mangaki/settings.py` :

    # EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

Ainsi, les mails seront affichés dans la console.

Nous contacter
--------------

En cas de pépin, [créez un ticket](https://bitbucket.org/mangaki/mangaki/issues) ou contactez-moi à vie@jill-jenn.net.
