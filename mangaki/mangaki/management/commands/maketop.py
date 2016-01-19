from django.core.management.base import BaseCommand, CommandError
from django.template import Context
from django.template.loader import get_template
from django.db.models import Count
from django.db import connection
from mangaki.models import Rating, Anime
from collections import Counter
import json


class Command(BaseCommand):
    args = ''
    help = 'Builds static page for top'

    def add_arguments(self, parser):
        parser.add_argument('json_path', nargs=1, type=str)
        parser.add_argument('category_slug', nargs=1, type=str)

    def handle(self, *args, **options):
        categories = {'directors': 'réalisateurs', 'composers': 'compositeurs', 'authors': 'auteurs'}
        json_path = options.get('json_path')[0]
        category_slug = options.get('category_slug')[0]
        top = json.load(open('%s.json' % json_path))
        for line in top:
            print(line)
        with open('mangaki/static/top/%s/index.html' % category_slug, 'w') as f:
            f.write(get_template('top.html').render(Context({'category': categories[category_slug], 'category_slug': category_slug, 'top': top})))
