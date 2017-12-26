from time import sleep
import json

from django.core.management.base import BaseCommand

from mangaki.wrappers.anilist import client, AniListWorkType
from mangaki.models import Work


MAX_ATTEMPTS = 5
BACKOFF_DELAY = 2

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
            title_display = work.title.encode('utf8').decode(self.stdout.encoding)

            anilist_search = None
            anilist_result = None
            worktype = None

            # Associate the right worktype or exit if not correct
            if work.category.slug == 'anime':
                worktype = AniListWorkType.ANIME
            elif work.category.slug == 'manga':
                worktype = AniListWorkType.MANGA
            else:
                continue

            # Try to fetch data from AniList with an exponential backoff
            for tries in range(MAX_ATTEMPTS):
                try:
                    # Search the work by title on AniList and then by ID if possible
                    anilist_search = client.get_work_by_title(worktype, work.title)
                    if anilist_search:
                        anilist_result = client.get_work_by_id(worktype, anilist_search.anilist_id)
                    break
                except Exception as err:
                    print(err)
                    delay = BACKOFF_DELAY ** tries
                    self.stdout.write(self.style.WARNING('Sleep : Retrying {} in {} seconds ...'.format(title_display, delay)))
                    sleep(delay)
                    continue

            # Couldn't fetch data even after retrying : exit
            if tries >= MAX_ATTEMPTS - 1:
                self.stderr.write(self.style.ERROR('\nBanned from AniList ...'))
                self.stderr.write(self.style.ERROR('--- Latest Work ID : '+str(work.pk)+' ---'))
                break

            # Work couldn't be found on Anilist
            if not anilist_result:
                missed_titles[work.id] = work.title
                self.stdout.write(self.style.WARNING('Could not match "'+str(title_display)+'" on AniList'))
                continue

            self.stdout.write('> Working on : '+str(title_display))

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

        self.stdout.write(self.style.SUCCESS('\n--- Writing tags to anilist_tags.json ---'))
        with open('anilist_tags.json', 'w', encoding='utf-8') as f:
            json.dump(final_tags, f)

        self.stdout.write(self.style.SUCCESS('--- Writing missed titles to missed_anilist_titles.json ---'))
        with open('missed_anilist_titles.json', 'w', encoding='utf-8') as f:
            json.dump(missed_titles, f)

        self.stdout.write(self.style.SUCCESS('--- Number of different tags : '+str(len(all_tags))+' ---'))
