from django.core.management.base import BaseCommand, CommandError

import os
import csv
from dedupe import Dedupe, consoleLabel, canonicalize
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
            with open(input_file, 'w', newline='') as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow(['id', 'title', 'vo_title'])
                for work_id in data:
                    title = data[work_id]['title']
                    if title != None:
                        title = title.encode('utf-8')
                    vo_title = data[work_id]['vo_title']
                    if vo_title != None:
                        vo_title = vo_title.encode('utf-8')
                    writer.writerow([work_id, title, vo_title])
            cluster_membership = {}
            cluster_id = 0
            for (cluster_id, cluster) in enumerate(clustered_dupes):
                id_set, scores = cluster
                cluster_d = [data[c] for c in id_set]
                canonical_rep = canonicalize(cluster_d)
                for record_id, score in zip(id_set, scores):
                    cluster_membership[record_id] = {
                        "cluster id" : cluster_id,
                        "canonical representation" : canonical_rep,
                        "confidence": score
                    }

            singleton_id = cluster_id + 1

            with open(output_file, 'w', newline='') as f_output, open(input_file) as f_input:
                writer = csv.writer(f_output, delimiter=",")
                reader = csv.reader(f_input)

                heading_row = next(reader)
                heading_row.insert(0, 'confidence_score')
                heading_row.insert(0, 'Cluster ID')
                canonical_keys = canonical_rep.keys()
                for key in canonical_keys:
                    heading_row.append('canonical_' + key)

                writer.writerow(heading_row)

                for row in reader:
                    row_id = int(row[0])
                    if row_id in cluster_membership:
                        cluster_id = cluster_membership[row_id]["cluster id"]
                        canonical_rep = cluster_membership[row_id]["canonical representation"]
                        row.insert(0, cluster_membership[row_id]['confidence'])
                        row.insert(0, cluster_id)
                        for key in canonical_keys:
                            row.append(canonical_rep[key].encode('utf8'))
                    else:
                        row.insert(0, None)
                        row.insert(0, singleton_id)
                        singleton_id += 1
                        for key in canonical_keys:
                            row.append(None)
                    writer.writerow(row)
            print('output file written')

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
            with open(input_file, 'w', newline='') as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow(['id', 'title', 'vo_title'])
                for work_id in data:
                    title = data[work_id]['title']
                    if title != None:
                        title = title.encode('utf-8')
                    vo_title = data[work_id]['vo_title']
                    if vo_title != None:
                        vo_title = vo_title.encode('utf-8')
                    writer.writerow([work_id, title, vo_title])

            cluster_membership = {}
            cluster_id = 0
            for (cluster_id, cluster) in enumerate(clustered_dupes):
                id_set, scores = cluster
                cluster_d = [data[c] for c in id_set]
                canonical_rep = canonicalize(cluster_d)
                for record_id, score in zip(id_set, scores):
                    cluster_membership[record_id] = {
                        "cluster id" : cluster_id,
                        "canonical representation" : canonical_rep,
                        "confidence": score
                    }

            singleton_id = cluster_id + 1

            with open(output_file, 'w', newline='') as f_output, open(input_file) as f_input:
                writer = csv.writer(f_output, delimiter=",")
                reader = csv.reader(f_input)

                heading_row = next(reader)
                heading_row.insert(0, 'confidence_score')
                heading_row.insert(0, 'Cluster ID')
                canonical_keys = canonical_rep.keys()
                for key in canonical_keys:
                    heading_row.append('canonical_' + key)

                writer.writerow(heading_row)

                for row in reader:
                    row_id = int(row[0])
                    if row_id in cluster_membership:
                        cluster_id = cluster_membership[row_id]["cluster id"]
                        canonical_rep = cluster_membership[row_id]["canonical representation"]
                        row.insert(0, cluster_membership[row_id]['confidence'])
                        row.insert(0, cluster_id)
                        for key in canonical_keys:
                            row.append(canonical_rep[key].encode('utf8'))
                    else:
                        row.insert(0, None)
                        row.insert(0, singleton_id)
                        singleton_id += 1
                        for key in canonical_keys:
                            row.append(None)
                    writer.writerow(row)
            print('output file written')

