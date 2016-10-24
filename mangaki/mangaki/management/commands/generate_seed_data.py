from django.core.management.base import BaseCommand
from django.core.management import call_command
from mangaki.models import *
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from collections import Counter
from django.db import connection, connections
from django.utils import timezone
from io import StringIO

import random
import json

PARAMETERS = {
    'small': {
        'max_anime': 20,
        'max_manga': 20
    },
    'big': {
        'max_anime': 200,
        'max_manga': 200
    }
}

def create_fixture(*parameters):
    buf = StringIO()
    call_command('dumpdata', *parameters, stdout=buf)
    buf.seek(0)
    return buf

def limit(mapping, items):
    limited_items = []
    counts = {key: 0 for key in mapping.keys()}
    for item in items:
        for key, limit_params in mapping.items():
            test, size = limit_params
            if test(item):
                if counts[key] < size:
                    limited_items.append(item)
                    counts[key] += 1
                else:
                    break
        else:
            limited_items.append(item)

    return limited_items

def fix_work_ids(items):
    new_items = []
    work_ids = set([i['pk'] for i in items if i['model'] == 'mangaki.work'])

    for item in items:
        if 'work' in item['fields'] and item['fields']['work'] in work_ids:
            new_items.append(item)

    return new_items

def test_anime(model_row):
    return model_row['model'] == 'mangaki.work' and model_row['fields']['category'] == 1

def test_manga(model_row):
    return model_row['model'] == 'mangaki.work' and model_row['fields']['category'] == 2


class Command(BaseCommand):
    args = ''
    help = 'Generate (small or big) seed data'

    def add_arguments(self, parser):
        parser.add_argument('size', type=str, help='small or big')
        parser.add_argument('--filename', type=str, default='fixture.json',
                            help='Target path where the fixture will be written')

    def handle(self, *args, **options):
        size, filename = options.get('size'), options.get('filename')
        print('Generating a {} seed data to {}'.format(size.lower(), filename))

        models_to_dump = [
            Category,
            Work,
            Role,
            Staff,
            Editor,
            Studio,
            Genre,
            Track,
            Artist,
            ArtistSpelling,
            Top,
            Ranking
        ]

        models = ['mangaki.{}'.format(model.__name__.lower()) for model in models_to_dump]
        fixture_data = json.loads(create_fixture(*models).read())
        print ('Limiting the data.')

        # Limit animes and mangas
        mapping = {
            'animes': (test_anime, PARAMETERS[size]['max_anime']),
            'manga': (test_manga, PARAMETERS[size]['max_manga'])
        }

        final_fixture = fix_work_ids(limit(mapping, fixture_data))

        with open(filename, 'w') as f:
            f.write(json.dumps(final_fixture))
        print ('Fixture ready.')
