from django.core.management.base import BaseCommand, CommandError
from mangaki.utils.anidb import AniDB
from mangaki.models import Anime


class Command(BaseCommand):
    args = ''
    help = 'Pair with AniDB'

    def handle(self, *args, **options):
        category = 'anime';
        work_query = 'SELECT mangaki_{category}.work_ptr_id, mangaki_work.id, mangaki_work.title, mangaki_work.poster, mangaki_work.nsfw, COUNT(mangaki_work.id) rating_count FROM mangaki_{category}, mangaki_work, mangaki_rating WHERE mangaki_{category}.work_ptr_id = mangaki_work.id AND mangaki_rating.work_id = mangaki_work.id AND mangaki_{category}.anidb_aid = 0 GROUP BY mangaki_work.id, mangaki_{category}.work_ptr_id HAVING COUNT(mangaki_work.id) >= {min_ratings} ORDER BY {order_by}'
        a = AniDB('mangakihttp', 1)
        for anime in Anime.objects.raw(work_query.format(category=category, min_ratings=6, order_by='rating_count DESC')):
            print(anime.title, anime.id)
            for proposal in a.search(r'\%s' % anime.title):
                print(proposal)
            anidb_aid = input('Which one? ')
            if anidb_aid == 'q':
                break
            anime.anidb_aid = int(anidb_aid)
            anime.save()
