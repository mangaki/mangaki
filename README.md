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

    virtualenv -p `which python3` venv
    . venv/bin/activate
    pip install -r requirements.txt
    cd mangaki
    cp secret_template.py secret.py  # À modifier
    ./manage.py migrate
    ./manage.py runserver

Remarques utiles
----------------

Si vous vous rendez sur la page des anime, ça chargera en boucle. C'est normal, il n'y a pas encore d'anime dans la base.

Si vous vous inscrivez, vous obtiendrez une erreur « Connection refused ». C'est normal, votre serveur de mails n'est pas installé. Pour éviter ce comportement temporairement, vous pouvez décommenter la ligne suivante de `mangaki/settings.py` :

    # EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

Ainsi, les mails seront affichés dans la console.

Nous contacter
--------------

En cas de pépin, [créez un ticket](https://bitbucket.org/mangaki/mangaki/issues) ou contactez-moi à vie@jill-jenn.net.
