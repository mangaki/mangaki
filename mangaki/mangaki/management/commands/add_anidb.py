from django.core.management.base import BaseCommand, CommandError
from mangaki.utils.anidb import AniDB
from mangaki.models import Work, Category
from django.db.models import Count
from urllib.parse import urlparse, parse_qs
import sys

def create_anime(**kwargs):
    anime = Category.objects.get(slug='anime')
    if 'anidb_aid' in kwargs:
        return Work.objects.update_or_create(category=anime, anidb_aid=kwargs['anidb_aid'], defaults=kwargs)[0]
    else:
        return Work.objects.create(category=anime, **kwargs)

class Command(BaseCommand):
    args = ''
    help = 'Retrieve AniDB data'

    def add_arguments(self, parser):
        parser.add_argument('id', type=int)

    def handle(self, *args, **options):        
        if options.get('id'):
            print(options.get('id'))
            anidb = AniDB('mangakihttp', 1)
            anime = create_anime(**anidb.get(options.get('id')))
            print(anime)
            anime.retrieve_poster()
