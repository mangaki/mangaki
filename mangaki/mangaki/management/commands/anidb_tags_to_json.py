from time import sleep
import json

from django.core.management.base import BaseCommand

from mangaki.utils.anidb import client
from mangaki.models import Work, Tag, TaggedWork
import logging


class Command(BaseCommand):
    """
    Utilise les valeurs d'AniDB ID déjà présentes dans la base de données
    et récupère les tags depuis AniDB pour chaque Work. Enfin, sort un
    fichier JSON contenant, pour chaque Work la liste des tags et le poids
    associé (valeur de 0 à 1).

    Le format du JSON est le même que pour illustration2vec !
    """

    args = ''
    help = 'AniDB tags to JSON'

    def handle(self, *args, **options):
        works = Work.objects.all().order_by('pk')
        final_tags = {}
        all_tags = set()

        count = Work.objects.exclude(anidb_aid=0).count()
        logging.info('Number of works with AniDB AID : '+str(count)+'\n')

        for work in works:
            if not work.anidb_aid:
                continue

            logging.info('> Working on : '+str(work))

            dict_key = '{}.jpg'.format(work.pk)
            tags_list = []

            try:
                # Ou handle_tags à la place de get_tags si pas encore renommé
                work_tags = client.get_tags(anidb_aid=work.anidb_aid)
            except Exception:
                logging.error('--- Banned from AniDB ---')
                logging.error('--- Latest Work ID : '+str(work.pk)+' ---')
                break

            for tag_title, tag_infos in work_tags.items():
                weight = tag_infos['weight']/600
                if weight != 0:
                    tags_list.append([tag_title, weight])
                    all_tags.add(tag_title)

            final_tags[dict_key] = tags_list

            logging.info('> Sleeping')
            sleep(1)

        logging.info('\n--- Writing tags to anidb_tags.json ---')
        with open('anidb_tags.json', 'w', encoding='utf-8') as f:
            json.dump(final_tags, f)

        logging.info('\nNumber of different tags : '+str(len(all_tags)))
