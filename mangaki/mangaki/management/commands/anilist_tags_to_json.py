from time import sleep
import json

from django.core.management.base import BaseCommand

from mangaki.wrappers.anilist import client, AniListWorks, AniListRichEntry
from mangaki.models import Work, Tag, TaggedWork
import logging


class Command(BaseCommand):
    """
    Recherche par titre chaque Work sur AniList puis récupère l'ID du Work
    chez AniList afin de finalement récupérer les tags (2 requêtes AniList à
    chaque Work). Si un titre ne match pas sur AniList, le log l'affiche et
    un fichier stocke l'ensemble des Work non récupérés (ID + Titre sur la BDD).
    Enfin, sort un fichier JSON contenant, pour chaque Work la liste des tags
    et le poids associé (valeur de 0 à 1) récupéré grâce au système de votes
    d'AniList.

    Le format du JSON est le même que pour illustration2vec !
    """

    args = ''
    help = 'AniList tags to JSON'

    def handle(self, *args, **options):
        works = Work.objects.all().order_by('pk')
        final_tags = {}
        all_tags = set()
        missed_titles = {}

        for work in works:
            try:
                if str(work.category) == 'Anime':
                    anilist_search = client.get_work_by_title(AniListWorks.animes, work.title)
                elif str(work.category) == 'Manga':
                    anilist_search = client.get_work_by_title(AniListWorks.mangas, work.title)
                else:
                    missed_titles[work.id] = work.title
                    logging.info('--- Could not match "'+str(work.title)+'" on AniList ---')
                    continue

                if str(work.category) == 'Anime' and anilist_search:
                    anilist_result = client.get_work_by_id(AniListWorks.animes, anilist_search.anilist_id)
                elif str(work.category) == 'Manga' and anilist_search:
                    anilist_result = client.get_work_by_id(AniListWorks.mangas, anilist_search.anilist_id)
                else:
                    missed_titles[work.id] = work.title
                    logging.info('--- Could not match "'+str(work.title)+'" on AniList ---')
                    continue
            except Exception:
                logging.error('--- Probably banned from AniList ---')
                logging.error('--- Latest Work ID : '+str(work.pk)+' ---')
                break

            logging.info('> Working on : '+str(anilist_result.title))

            dict_key = '{}.jpg'.format(work.pk)
            tags_list = []

            if not anilist_result.tags:
                continue

            for tag in anilist_result.tags:
                tag_name = tag['name']
                tag_weight = tag['votes']/100
                tags_list.append([tag_name, tag_weight])
                all_tags.add(tag_name)

            final_tags[dict_key] = tags_list

            logging.info('> Sleeping')
            sleep(1)

        logging.info('\n--- Writing tags to anilist_tags.json ---')
        with open('anilist_tags.json', 'w', encoding='utf-8') as f:
            json.dump(final_tags, f)

        logging.info('--- Writing missed titles to missed_anilist_titles.json ---')
        with open('missed_anilist_titles.json', 'w', encoding='utf-8') as f:
            json.dump(missed_titles, f)

        logging.info('\nNumber of different tags : '+str(len(all_tags)))
