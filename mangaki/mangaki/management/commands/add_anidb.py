from django.core.management.base import BaseCommand
from mangaki.utils.anidb import AniDB
from mangaki.models import WorkTitle


def create_anime(work, work_titles):
    work.save()
    for title in work_titles:
        title.work = work
    WorkTitle.objects.bulk_create(work_titles)
    return work


class Command(BaseCommand):
    args = ''
    help = 'Retrieve AniDB data'

    def add_arguments(self, parser):
        parser.add_argument('id', type=int)

    def handle(self, *args, **options):
        anidb = AniDB('mangakihttp', 1)
        anime = create_anime(*anidb.get_mangaki_work(options.get('id')))
        anime.retrieve_poster()  # Save for future use
        self.stdout.write(self.style.SUCCESS('Successfully added %s' % anime))
