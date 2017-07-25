from time import sleep
import json

from django.core.management.base import BaseCommand

from mangaki.wrappers.anilist import client, AniListWorks
from mangaki.models import Work


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

    help = 'AniList tags to JSON'

    def add_arguments(self, parser):
        parser.add_argument('work_id', nargs='*', type=int)

    def handle(self, *args, **options):
        if options['work_id']:
            works = Work.objects.filter(pk__in=options['work_id']).order_by('pk')
        else:
            works = Work.objects.all().order_by('pk')

        if works.count() == 0:
            self.stdout.write(self.style.WARNING('No works to process ...'))
            return

        final_tags = {}
        all_tags = set()
        missed_titles = {}

        count = works.count()
        self.stdout.write('Number of works : '+str(count)+'\n\n')

        for work in works:
            try:
                anilist_search = None

                # Search the work by title on AniList
                if work.category.slug == 'anime':
                    anilist_search = client.get_work_by_title(AniListWorks.animes, work.title)
                elif work.category.slug == 'manga':
                    anilist_search = client.get_work_by_title(AniListWorks.mangas, work.title)

                # Then seek the whole information of the work thanks to its ID, if possible
                if work.category.slug == 'anime' and anilist_search:
                    anilist_result = client.get_work_by_id(AniListWorks.animes, anilist_search.anilist_id)
                elif work.category.slug == 'manga' and anilist_search:
                    anilist_result = client.get_work_by_id(AniListWorks.mangas, anilist_search.anilist_id)
                else:
                    missed_titles[work.id] = work.title
                    self.stdout.write(self.style.WARNING('Could not match "'+str(work.title)+'" on AniList'))
                    continue
            except Exception:
                self.stderr.write(self.style.ERROR('Banned from AniList ...'))
                self.stderr.write(self.style.ERROR('--- Latest Work ID : '+str(work.pk)+' ---'))
                break

            self.stdout.write('> Working on : '+str(anilist_result.title))

            dict_key = '{}.jpg'.format(work.pk)
            tags_list = []

            if not anilist_result.tags:
                continue

            for tag in anilist_result.tags:
                tag_name = tag['name']
                tag_weight = tag['votes']/100
                if tag_weight != 0:
                    tags_list.append([tag_name, tag_weight])
                    all_tags.add(tag_name)

            final_tags[dict_key] = tags_list

            self.stdout.write('> Sleeping')
            sleep(1)

        self.stdout.write(self.style.SUCCESS('\n--- Writing tags to anilist_tags.json ---'))
        with open('anilist_tags.json', 'w', encoding='utf-8') as f:
            json.dump(final_tags, f)

        self.stdout.write(self.style.SUCCESS('--- Writing missed titles to missed_anilist_titles.json ---'))
        with open('missed_anilist_titles.json', 'w', encoding='utf-8') as f:
            json.dump(missed_titles, f)

        self.stdout.write(self.style.SUCCESS('--- Number of different tags : '+str(len(all_tags))+' ---'))
