from collections import Counter
from itertools import groupby

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Count

from mangaki.models import Rating, Work
from mangaki.utils.ranking import controversy


class Command(BaseCommand):
    args = ''
    help = 'Analytics'

    def handle(self, *args, **options):
        anime_map = {}
        popular_anime = Work.objects.filter(category__slug='anime').annotate(Count('rating')).filter(rating__count__gte=100)
        for anime in popular_anime:
            anime_map[anime.id] = anime
        ratings = Rating.objects.filter(work__in=popular_anime).values('work', 'choice').annotate(count=Count('pk')).order_by('work', 'choice')
        print(len(popular_anime), 'anime')
        score = Counter()
        for anime, ratings in groupby(ratings, lambda rating: rating['work']):
            nb_likes = nb_dislikes = 0
            for rating in ratings:
                if rating['choice'] == 'like':
                    nb_likes = rating['count']
                elif rating['choice'] == 'dislike':
                    nb_dislikes = rating['count']
            # if nb_dislikes == 0:
            """if 'Baccano' in anime_map[anime].title:
                print(anime_map[anime].title, (nb_likes, nb_dislikes))"""
            # if nb_dislikes <= 2:
            nb = {
                'dislike': nb_dislikes,
                'like': nb_likes
            }
            score[(anime, (nb_likes, nb_dislikes))] = controversy(nb)
        print(len(score.keys()), 'anime après filtrage')
        for k, v in score.most_common(50):
            print(anime_map[k[0]].title, k[1], v, anime_map[k[0]].rating_set.count(), 'ratings')
        print(len(connection.queries))
