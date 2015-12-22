from django.core.management.base import BaseCommand, CommandError
from mangaki.models import Work, Rating, Deck
from django.db import connection
from django.db.models import Count
from collections import Counter
import random
import sys

TOP_MIN_RATINGS = 80
RANDOM_MIN_RATINGS = 28
RANDOM_MIN_DISLIKES = 17
RANDOM_RATIO = 3.0

def controversy(nb_likes, nb_dislikes):
    if nb_likes == 0 or nb_dislikes == 0:
        return 0
    return (nb_likes + nb_dislikes) ** min(float(nb_likes) / nb_dislikes, float(nb_dislikes) / nb_likes)


class Command(BaseCommand):
    args = ''
    help = 'Print ranking and make decks'

    def handle(self, *args, **options):
        rating_values = {'favorite': 5, 'like': 2.5, 'dislike': -2, 'neutral': -0.1, 'willsee': 0.5, 'wontsee': -0.5}
        sum_ratings = Counter()
        nb_ratings = Counter()
        nb_likes = Counter()
        nb_dislikes = Counter()
        category_of = {}
        for work_id, choice, is_anime in Rating.objects.values_list('work_id', 'choice', 'work__anime'):
            if choice not in ['willsee', 'wontsee']:
                sum_ratings[work_id] += rating_values[choice]
                nb_ratings[work_id] += 1
                if choice == 'like':
                    nb_likes[work_id] += 1
                elif choice == 'dislike':
                    nb_dislikes[work_id] += 1
                category_of[work_id] = 'anime' if is_anime else 'manga'

        sort_modes = ['top', 'popularity', 'controversy', 'random']
        ranking = {sort_mode: Counter() for sort_mode in sort_modes}
        is_eligible = {
            'top': lambda work_id: nb_ratings[work_id] >= TOP_MIN_RATINGS,
            'popularity': lambda x: True,
            'controversy': lambda x: True,
            'random': lambda x: nb_ratings[work_id] >= RANDOM_MIN_RATINGS and nb_dislikes[work_id] <= RANDOM_MIN_DISLIKES and ( nb_dislikes[work_id] == 0 or nb_likes[work_id] / nb_dislikes[work_id] >= RANDOM_RATIO)
        }
        score = {
            'top': lambda work_id: sum_ratings[work_id] / nb_ratings[work_id],
            'popularity': lambda work_id: nb_ratings[work_id],
            'controversy': lambda work_id: controversy(nb_likes[work_id], nb_dislikes[work_id]),
            'random': lambda work_id: sum_ratings[work_id] / nb_ratings[work_id]  # nb_likes[work_id] / nb_dislikes[work_id] if nb_dislikes[work_id] else float('inf')
        }
        for sort_mode in sort_modes:
            print('#', sort_mode)
            for work_id in nb_ratings:
                if is_eligible[sort_mode](work_id):
                    ranking[sort_mode][work_id] = score[sort_mode](work_id)
            works = Work.objects.in_bulk(ranking[sort_mode].keys())
            deck = {'anime': [], 'manga': []}
            rank = {'anime': 0, 'manga': 0}
            for work_id, value in ranking[sort_mode].most_common():
                category = category_of[work_id]
                rank[category] += 1
                if sort_mode == 'top' and category == 'anime' and rank[category] <= 50:
                    print('%2d.' % rank[category], category, works[work_id].title, value, nb_ratings[work_id], 'ratings', nb_likes[work_id], 'likes', nb_dislikes[work_id], 'dislikes', work_id)
                deck[category].append(str(work_id))
            for category in ['anime', 'manga']:
                print(','.join(deck[category])[:50])
                Deck.objects.filter(category=category, sort_mode=sort_mode).update(content=','.join(deck[category]))
