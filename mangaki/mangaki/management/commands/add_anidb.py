from django.core.management.base import BaseCommand
from mangaki.utils.anidb import AniDB
from mangaki.models import Work, Category
from urllib.parse import urlparse

def create_anime(**kwargs):
    anime = Category.objects.get(slug='anime')
    return Work.objects.update_or_create(category=anime, anidb_aid=kwargs['anidb_aid'], defaults=kwargs)[0]

class Command(BaseCommand):
    args = ''
    help = 'Retrieve AniDB data'

    def add_arguments(self, parser):
        parser.add_argument('id', type=int)

    def handle(self, *args, **options):
        anidb = AniDB('mangakihttp', 1)
        anime = create_anime(**anidb.get_dict(options.get('id')))
        anime.retrieve_poster()  # Save for future use
        self.stdout.write(self.style.SUCCESS('Successfully added %s' % anime))
