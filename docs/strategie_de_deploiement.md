# Stratégie de déploiement pour Mangaki

Nom de code: OPERATION VERDANDI.

## Préambule à propos des informations sensibles de Mangaki

Afin de simplifier la DX (developer experience, je viens de l'inventer, pas mal hein?), je suggère d'employer:

- une branche de production au sens propre du terme, elle sera le reflet du site mangaki.fr (en temps-réel)
- une branche de staging au sens propre du terme, elle sera le reflet du site staging.mangaki.fr (en temps-réel)

Cependant, pour éviter d'avoir des fichiers .env qui pendouillent un peu partout sur nos copies locales, je vous suggère d'employer le chiffrement:

- https://www.vaultproject.io
- PGP

Enfin, on utilisera des Git commit hooks pour chiffrer systématiquement les modifications aux variables sensibles (API Key, SSH Keys, etc...).

## Aperçu de l'architecture

À priori, notre architecture se constituera en plusieurs serveurs:

- le "front" serveur, qui aura simplement un NGINX et qui fera office de load-balancer vers les autres serveurs.
- le serveur de staging et de production seront dans un premier temps sur la même machine

Je propose que cette architecture soit hébergé sur DigitalOcean qui nous permettra plus facilement de gérer les machines que d'autres systèmes.
Le front serveur sera provisionné manuellement, et les fichiers de config seront tenu secrets dans un premier temps.
Quant au serveur de staging et de production, ils seront provisionné à l'aide d'Ansible, dont les fichiers de config seront en ligne (hors variables sensibles qui seront naturellement chiffrés).

## Utilité

Certains peuvent se demander la raison d'autant « d'overengineering », sans invoquer des raisons absurdes (scaling, future-proof, blablabla).
Dans un premier temps, il s'agit de mettre à plat et de simplifier la contribution à Mangaki autant pour les développeurs et les non-développeurs.
Dans un second temps, il s'agit aussi de poser de bonne base avant d'accumuler de la dette technique complètement inutile:
- NGINX ne compte pas disparaître
- DigitalOcean non plus
- Ansible à priori sera encore supporté pendant quelques années
- Les fichiers de config existent depuis pas mal de temps je pense
Enfin, il faut admettre qu'automatiser le déploiement de Mangaki est assez séduisant, car il abstrait une partie douloureuse qui me paraît une grosse perte de temps, entendez par là que je préfère améliorer Mangaki que déployer Mangaki, logique à mon sens.

## Déroulement d'une mise en production

Idéalement, j'aimerais pouvoir faire en sorte que le serveur de staging puissent détecter de nouveaux commits et `git pull` les derniers commits et relancer une opération de déploiement.

Quant au serveur de production, j'aimerais en faire de même mais pour une autre branche.

## Sauvegardes

À définir plus en détails. (DigitalOcean fournit des backups weekly).

## Workflow

Raito est un développeur, JJ est un intégrateur, afin de valider les modifications que Raito a faite dans une PR, JJ la merge dans `staging`.

Voilà ce qui se passera:

- `mangaki-staging` détecte les nouveaux commits et récupère le contenu des derniers commits (comprendre: `git pull`)
- `mangaki-staging` installe les nouvelles dépendances si il y a nécessité (comprendre: `pip install requirements.txt` et `npm install`)
- `mangaki-staging` lance les migrations si il y a nécessité (comprendre: `./manage.py migrate`)
- `mangaki-staging` recharge le worker Gunicorn par un signal USR1 (comprendre: `kill -USR1 $GUNICORN_MASTER`)
- `mangaki-staging` capture toutes les erreurs et les reporte via Slack dans un channel, si il y a succès, il le signifie.

À la fin de cette procédure, <dev.mangaki.fr> sera opérationnel et sera le reflet de la branche `staging`, Raito pourra tester ses modifications ainsi que JJ pourra vérifier qu'il n'y a pas de régressions.

Une fois que c'est bien vérifié, une nouvelle PR est crée vers `production`.

## Additions

Il serait encore meilleur de pouvoir ajouter des tâches du type:

- Lancer les tests unitaires et arrêter le déploiement si ils ne passent pas.
- Lancer les tests d'intégrations et arrêter le déploiement si ils ne passent pas.
- Penser au failover de Mangaki, que se passe-t-il si `mangaki-production` crash, devrions-nous penser à `mangaki-failover` ?
- Monitoring des serveurs et analytics au niveau du front serveur ? (Savoir quand on a des pics de trafic et faire de l'auto-scaling avec l'API de DigitalOcean! ^[1])

^[1]: J'ai toujours rêvé de faire ça!

## Coûts

J'aimerais pouvoir minimiser les coûts le plus possible, ainsi, je recommande dans un premier lieu, 2 serveurs.
Ce qui serait équivalent à 10\$/mois. Au prochain post-mortem, on analysera.

