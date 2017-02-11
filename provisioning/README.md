# Déploiement de Mangaki par Ansible

## Les secrets

Vous devez créer un fichier `env_vars/secret.yml` se basant sur ce format :

```
db_password: something_really_secure
secure_key: also_secure_i_guess

email_host: somewhere_in_the_internet.com
email_host_user: mangaki@myinstance.com
email_host_password: my_dope_password
```

Vous pouvez ajouter des informations en fonction des templates qui se trouvent dans `roles/web/templates/`, en particulier: [`roles/web/templates/settings.ini.j2`](roles/web/templates/settings.ini.j2).

## Le déploiement

Ajouter vos serveurs qui recevront tous une instance de Mangaki à `inventory` sous la forme :

```
[webservers]
100.100.100.100
1.2.3.4
5.6.7.8
```

## HTTPS et petits problèmes

Si vous n'avez pas au préalable modifier vos enregistrements DNS pour qu'ils pointent vers la bonne adresse IP.

Il est fort probable que vous rencontriez une erreur durant le déploiement, pas de panique. Il suffit d'ajouter l'enregistrement DNS et de recommencer le déploiement.

## Comment mettre à jour mon instance ?

Bonne question, on y travaille.
