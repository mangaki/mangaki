from collections import Counter
from mangaki.models import Rating, ColdStartRating, Work
from mangaki.utils.chrono import Chrono
from mangaki.utils.values import rating_values, rating_values_dpp
from django.contrib.auth.models import User
from django.db.models import Count
from django.db import connection

NB_NEIGHBORS = 15
MIN_RATINGS = 3

CHRONO_ENABLED = False

def get_recommendations(user, category, editor, dpp):
    # What if user is not authenticated? We will see soon.
    chrono = Chrono(CHRONO_ENABLED)

    chrono.save('[%dQ] begin' % len(connection.queries))

    rated_works = {}
    if dpp :
        qs = ColdStartRating.objects.filter(user=user).values_list('work_id', 'choice')
        
    else : 
        qs = Rating.objects.filter(user=user).values_list('work_id', 'choice')

    for work_id, choice in qs:
        rated_works[work_id] = choice

    willsee = set()
    if user.profile.reco_willsee_ok:
        banned_works = set()
        for work_id in rated_works:
            if rated_works[work_id] != 'willsee':
                banned_works.add(work_id)
            else:
                willsee.add(work_id)
    else:
        banned_works = set(rated_works.keys())

    mangas = Work.objects.filter(category__slug='manga')
    if editor == 'otototaifu':
        mangas = mangas.filter(editor__title__in=['Ototo Manga', 'Taifu comics'])
    elif editor != 'unspecified':
        mangas = mangas.filter(editor__title__icontains=editor)
    manga_ids = mangas.values_list('id', flat=True)

    kept_works = None
    if category == 'anime':
        banned_works |= set(manga_ids)
    elif category == 'manga':
        kept_works = set(manga_ids)

    chrono.save('[%dQ] retrieve her %d ratings' % (len(connection.queries), len(rated_works)))

    if dpp :
        values = rating_values
    else : 
        values = rating_values_dpp

    final_works = Counter()
    nb_ratings = {}
    c = 0
    neighbors = Counter()
    for user_id, work_id, choice in Rating.objects.filter(work__in=rated_works.keys()).values_list('user_id', 'work_id', 'choice'):
        c += 1
        neighbors[user_id] += values[rated_works[work_id]] * values[choice]

    chrono.save('[%dQ] fill neighbors with %d ratings' % (len(connection.queries), c))

    score_of_neighbor = {}
    # print('Neighbors:')
    # nbr = []
    for user_id, score in neighbors.most_common(NB_NEIGHBORS):
        # print(User.objects.get(id=user_id).username, score)
        score_of_neighbor[user_id] = score
        # nbr.append(user_id)
    # print(nbr)

    sum_ratings = Counter()
    nb_ratings = Counter()
    sum_scores = Counter()
    i = 0
    for work_id, user_id, choice in Rating.objects.filter(user__id__in=score_of_neighbor.keys()).exclude(choice__in=['willsee', 'wontsee']).values_list('work_id', 'user_id', 'choice'):
        i += 1
        if work_id in banned_works or (kept_works and work_id not in kept_works):
            continue

        sum_ratings[work_id] += values[choice]
        nb_ratings[work_id] += 1
        sum_scores[work_id] += score_of_neighbor[user_id]

    chrono.save('[%dQ] compute and filter all ratings from %d sources' % (len(connection.queries), i))

    i = 0
    k = 0
    for work_id in nb_ratings:
        # Adding interesting works to the arena (rated at least MIN_RATINGS by neighbors)
        if nb_ratings[work_id] >= MIN_RATINGS:
            k += 1
            final_works[(work_id, work_id in manga_ids, work_id in willsee)] = (float(sum_ratings[work_id]) / nb_ratings[work_id], sum_scores[work_id])    
        i += 1

    chrono.save('[%dQ] rank %d %d works' % (len(connection.queries), k, i))

    reco = []
    rank = 0
    rank_of = {}
    for (work_id, is_manga, in_willsee), _ in final_works.most_common(4):  # Retrieving top 4
        rank_of[work_id] = rank
        reco.append([work_id, is_manga, in_willsee])
        rank += 1

    works = Work.objects.filter(id__in=rank_of.keys())
    for work in works:
        reco[rank_of[work.id]][0] = work

    # print(len(connection.queries), 'queries')
    """for line in connection.queries:
        print(line)"""

    chrono.save('[%dQ] retrieve top 4' % len(connection.queries))

    return reco
