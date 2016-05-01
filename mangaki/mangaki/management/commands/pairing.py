from django.core.management.base import BaseCommand, CommandError
from mangaki.utils.anidb import AniDB
from django.db.models import Count
from mangaki.models import Work


class Command(BaseCommand):
    args = ''
    help = 'Pair with AniDB'

    def handle(self, *args, **options):
        q = Work.objects\
                .only('pk', 'title', 'poster', 'nsfw')\
                .annotate(rating_count=Count('rating'))\
                .filter(anidb_aid=0, category='anime', rating_count__gte=6)\
                .order_by('-rating_count')
        a = AniDB('mangakihttp', 1)
        for anime in q:
            print(anime.title, anime.id)
            for proposal in a.search(r'\%s' % anime.title):
                print(proposal)
            anidb_aid = input('Which one? ')
            if anidb_aid == 'q':
                continue
            anime.anidb_aid = int(anidb_aid)
            anime.save()
