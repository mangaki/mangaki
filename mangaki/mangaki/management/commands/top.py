from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.db import connection
from mangaki.models import Rating, Anime, Artist
from mangaki.utils.chrono import Chrono
from collections import Counter
import json
import sys

class Command(BaseCommand):
    args = ''
    help = 'Builds top'
    def handle(self, *args, **options):
        chrono = Chrono(False)
        category = sys.argv[2]
        c = Counter()
        values = {'favorite': 10, 'like': 2, 'neutral': 0.5, 'dislike': -1}
        nb_ratings = Counter()
        nb_stars = Counter()
        for choice, contestant_id in Rating.objects.values_list('choice', 'work__anime__' + category):
            if contestant_id and contestant_id > 1:  # Artiste non inconnu
                nb_ratings[contestant_id] += 1
                if choice == 'favorite':
                    nb_stars[contestant_id] += 1
                c[contestant_id] += values.get(choice, 0)
        chrono.save('enter contestants')
        artist_ids = []
        for artist_id, _ in c.most_common(20):
            artist_ids.append(artist_id)
        artist_by_id = Artist.objects.in_bulk(artist_ids)
        top = []
        for i, (artist_id, score) in enumerate(c.most_common(20)):
            top.append(dict(rank=i + 1, name=str(artist_by_id[artist_id]), id=artist_id, score=score, nb_ratings=nb_ratings[artist_id], nb_stars=nb_stars[artist_id]))
        chrono.save('get results')
        # print('%d queries' % len(connection.queries))
        print(json.dumps(top))
