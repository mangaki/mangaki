from time import sleep
import json

from django.core.management.base import BaseCommand

from mangaki.utils.anidb import client
from mangaki.models import Work


ATTEMPTS_THRESHOLD = 5
BACKOFF_DELAY = 2

class Command(BaseCommand):
    """
    Utilise les valeurs d'AniDB ID déjà présentes dans la base de données
    et récupère les tags depuis AniDB pour chaque Work. Enfin, sort un
    fichier JSON contenant, pour chaque Work la liste des tags et le poids
    associé (valeur de 0 à 1).

    Le format du JSON est le même que pour illustration2vec !
    """

    help = 'AniDB tags to JSON'

    def add_arguments(self, parser):
        parser.add_argument('work_id', nargs='*', type=int)

    def handle(self, *args, **options):
        if options['work_id']:
            works = Work.objects.exclude(anidb_aid=0).filter(pk__in=options['work_id']).order_by('pk')
        else:
            works = Work.objects.exclude(anidb_aid=0).all().order_by('pk')

        if works.count() == 0:
            self.stdout.write(self.style.WARNING('No works to process ...'))
            return

        final_tags = {}
        all_tags = set()

        count = works.count()
        self.stdout.write('Number of works : '+str(count)+'\n\n')

        for work in works:
            title_display = work.title.encode('utf8').decode(self.stdout.encoding)
            tries = 0
            delay = 0

            if not work.anidb_aid:
                continue

            # Try to fetch data from AniDB with an exponential backoff
            while True:
                try:
                    # Retrieve tags for the current Work
                    work_tags = client.get_tags(anidb_aid=work.anidb_aid)
                    break
                except:
                    delay = BACKOFF_DELAY**tries

                    message = 'Sleep : Retrying {} in {} seconds ...'.format(title_display, delay)
                    style = self.style.WARNING

                    if tries > ATTEMPTS_THRESHOLD:
                        message += ' [Might be banned]'
                        style = self.style.ERROR

                    self.stdout.write(style(message))
                    sleep(delay)
                    tries += 1
                    continue

            self.stdout.write('> Working on : '+str(title_display))

            dict_key = '{}.jpg'.format(work.pk)
            tags_list = []

            if not work_tags:
                continue

            for tag_title, tag_infos in work_tags.items():
                weight = tag_infos['weight']/600
                if weight != 0:
                    tags_list.append([tag_title, weight])
                    all_tags.add(tag_title)

            final_tags[dict_key] = tags_list

        self.stdout.write(self.style.SUCCESS('\n--- Writing tags to anidb_tags.json ---'))
        with open('anidb_tags.json', 'w', encoding='utf-8') as f:
            json.dump(final_tags, f)

        self.stdout.write(self.style.SUCCESS('--- Number of different tags : '+str(len(all_tags))+' ---'))
