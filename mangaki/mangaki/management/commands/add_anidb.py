from django.core.management.base import BaseCommand
from mangaki.utils.anidb import client


class Command(BaseCommand):
    args = ''
    help = 'Retrieve AniDB data'

    def add_arguments(self, parser):
        parser.add_argument('id', type=int)

    def handle(self, *args, **options):
        anime = client.get_or_update_work(options.get('id'))
        anime.retrieve_poster()  # Save for future use
        self.stdout.write(self.style.SUCCESS('Successfully added %s' % anime))
