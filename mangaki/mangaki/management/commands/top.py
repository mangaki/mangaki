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
        values = {'favorite': 2, 'like': 1, 'neutral': 0.5, 'dislike': 0}
        anime_ids = Anime.objects.values_list('id', flat=True)
        for rating in Rating.objects.select_related('work__anime__' + category):
            if rating.work_id in anime_ids:
                c[getattr(rating.work.anime, category)] += values.get(rating.choice, 0)
        for i, k, v in enumerate(c.most_common(10)):
            print('%d.' % (i + 1), k, v)
        print(len(connection.queries), 'queries')
