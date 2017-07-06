#!/bin/sh

export VIRTUALENV_PATH=/home/vagrant/.virtualenv

# Installation de paquets
apt-get update && apt-get install -y python3-dev python3-pip postgresql python3-sqlparse pwgen git libpq-dev python3-numpy python3-scipy postgresql-contrib

# Configuration de postgresql
sudo -u postgres -H createdb mangaki
sudo -u postgres -H createuser django
export DB_PASSWORD=$(pwgen -s -c 30 1)
sudo -u postgres -H psql -d mangaki -c "\
  create extension if not exists pg_trgm; \
  create extension if not exists unaccent; \
  alter user django with password '$DB_PASSWORD'; \
  grant all privileges on database mangaki to django"

# Mise en place du .bash_profile pour configurer le `vagrant ssh`
cat > ~vagrant/.bash_profile <<EOF
# On veut les utilitaires python dans le PATH
export PATH="\$PATH:\$HOME/.local/bin"

# Mangaki est installé dans /vagrant
cd /vagrant/mangaki

source $VIRTUALENV_PATH/bin/activate
EOF
chown vagrant:vagrant ~vagrant/.bash_profile

# Configuration de Mangaki
cat > /vagrant/mangaki/settings.ini <<EOF
[debug]
DEBUG = True

[hosts]
ALLOWED_HOSTS = *

[secrets]
SECRET_KEY = $(pwgen -s -c 60 1)
DB_PASSWORD = ${DB_PASSWORD}

[email]
EMAIL_BACKEND = django.core.mail.backends.console.EmailBackend
EOF

# We install a virtualenv as a user.
sudo -H -u vagrant pip3 install --user virtualenv
sudo -H -u vagrant /home/vagrant/.local/bin/virtualenv --python=python3 $VIRTUALENV_PATH
echo 'Virtual environment built.'
sudo -H -u vagrant $VIRTUALENV_PATH/bin/pip install -r /vagrant/requirements.txt
sudo -H -u vagrant $VIRTUALENV_PATH/bin/pip install -r /vagrant/requirements/dev.txt
sudo -H -u vagrant $VIRTUALENV_PATH/bin/pip install scikit-learn
echo 'Dependencies installed.'

# On va dans le dossier où est installé Mangaki
cd /vagrant/mangaki

# Configuration de la base de données
sudo -H -u vagrant $VIRTUALENV_PATH/bin/python manage.py migrate
# sudo -H -u vagrant python3 manage.py loaddata ../fixtures/{partners,ghibli,kizu,seed_data}.json
# sudo -H -u vagrant python3 manage.py ranking
# sudo -H -u vagrant python3 manage.py top director
