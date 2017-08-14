from django.core.management.base import BaseCommand, CommandError

import os
import csv
from dedupe import Dedupe, consoleLabel
from mangaki.models import Work




class Command(BaseCommand):
    args = ''
    help = 'Make training of dedupe with mangas or animes'

    def add_arguments(self, parser):
        parser.add_argument('myargs', nargs='+', type=str)

    def handle(self, *args, **options):
        category = str(options['myargs'][0])
        if category == 'mangas':
            data = {}
            for work in Work.objects.filter(category__slug='manga'):
                data[work.id] = {'title': work.title, 'vo_title': work.vo_title}
                for field in ['title', 'vo_title']:
                   if not data[work.id][field]:
                        data[work.id][field] = None
            fields = [
                {'field': 'title', 'type': 'String'},
                {'field': 'vo_title', 'type': 'String'},
            ]

            output_file = 'dedupe/mangas_output.csv'
            settings_file = 'dedupe/mangas_learned_settings'
            training_file = 'dedupe/mangas_training.json'

            deduper = Dedupe(fields)
            deduper.sample(data)
            consoleLabel(deduper)

            if os.path.exists(training_file):
                print('reading labeled examples from ', training_file)
                with open(training_file, 'rb') as f:
                    deduper.readTraining(f)

            deduper.train()

            with open(training_file, 'w') as tf:
                deduper.writeTraining(tf)

            with open(settings_file, 'wb') as sf:
                deduper.writeSettings(sf)

            threshold = deduper.threshold(data, recall_weight=2)

            print('clustering...')
            clustered_dupes = deduper.match(data, threshold)

            print('# duplicate sets', len(clustered_dupes))
            input_file = 'dedupe/mangas.csv'
            with open(input_file, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'title', 'vo_title'])
                for work_id in data:
                    title = data[work_id]['title']
                    if title != None:
                        title = title.encode('utf-8')
                    vo_title = data[work_id]['vo_title']
                    if vo_title != None:
                        vo_title = vo_title.encode('utf-8')
                    writer.writerow([work_id, title, vo_title])

        elif category == 'animes':
            data = {}
            for work in Work.objects.filter(category__slug='anime'):
                data[work.id] = {'title': work.title, 'vo_title': work.vo_title}
                for field in ['title', 'vo_title']:
                    if not data[work.id][field]:
                        data[work.id][field] = None
            fields = [
                {'field': 'title', 'type': 'String'},
                {'field': 'vo_title', 'type': 'String'},
            ]

            output_file = 'dedupe/animes_output.csv'
            settings_file = 'dedupe/animes_learned_settings'
            training_file = 'dedupe/animes_training.json'

            deduper = Dedupe(fields)
            deduper.sample(data)
            consoleLabel(deduper)

            if os.path.exists(training_file):
                print('reading labeled examples from ', training_file)
                with open(training_file, 'rb') as f:
                    deduper.readTraining(f)

            deduper.train()

            with open(training_file, 'w') as tf:
                deduper.writeTraining(tf)

            with open(settings_file, 'wb') as sf:
                deduper.writeSettings(sf)

            threshold = deduper.threshold(data, recall_weight=2)

            print('clustering...')
            clustered_dupes = deduper.match(data, threshold)

            print('# duplicate sets', len(clustered_dupes))
            input_file = 'dedupe/animes.csv'
            with open(input_file, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'title', 'vo_title'])
                for work_id in data:
                    title = data[work_id]['title']
                    if title != None:
                        title = title.encode('utf-8')
                    vo_title = data[work_id]['vo_title']
                    if vo_title != None:
                        vo_title = vo_title.encode('utf-8')
                    writer.writerow([work_id, title, vo_title])