from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.db import connection
from mangaki.models import Rating, Anime
from collections import Counter
import json

class Command(BaseCommand):
    args = ''
    help = 'Builds top'
    def handle(self, *args, **options):
        category = 'composer'
        c = Counter()
        values = {'favorite': 10, 'like': 2, 'neutral': 0.5, 'dislike': -1}
        anime_ids = Anime.objects.exclude(composer=1).values_list('id', flat=True)
        nb_ratings = Counter()
        nb_stars = Counter()
        for rating in Rating.objects.filter(work_id__in=anime_ids).select_related('work__anime__' + category):
            contestant = getattr(rating.work.anime, category)
            nb_ratings[contestant] += 1
            if rating.choice == 'favorite':
                nb_stars[contestant] += 1
            c[contestant] += values.get(rating.choice, 0)
        top = []
        for i, (artist, score) in enumerate(c.most_common(20)):
            top.append(dict(rank=i + 1, name=str(artist), score=score, nb_ratings=nb_ratings[artist], nb_stars=nb_stars[artist]))
        print(json.dumps(top))
