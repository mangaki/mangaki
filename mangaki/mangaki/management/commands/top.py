from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.db import connection
from mangaki.models import Rating, Anime
from collections import Counter

class Command(BaseCommand):
    args = ''
    help = 'Builds top'
    def handle(self, *args, **options):
        category = 'composer'
        c = Counter()
        values = {'favorite': 10, 'like': 1, 'neutral': 0.5, 'dislike': 0}
        anime_ids = Anime.objects.filter(anidb_aid__gt=0).values_list('id', flat=True)
        nb_ratings = {}
        for rating in Rating.objects.filter(work_id__in=anime_ids).select_related('work__anime__' + category):
            contestant = getattr(rating.work.anime, category)
            if contestant in nb_ratings:
                nb_ratings[contestant] += 1
            else:
                nb_ratings[contestant] = 1
            try:
                c[contestant] += values.get(rating.choice, 0)
            except:
                print(rating)
        for k in c:
            c[k] /= nb_ratings[k]
        for i, (k, v) in enumerate(c.most_common(10)):
            print('%d.' % (i + 1), k, v)
        print(len(connection.queries), 'queries')
