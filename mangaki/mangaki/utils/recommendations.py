from collections import Counter
from mangaki.models import Manga, Rating
from django.contrib.auth.models import User
from django.db.models import Count

def get_recommendations(user, my_rated_works, category):
    values = {
        'like': 2,
        'dislike': -2,
        'neutral': 0.1,
        'willsee': 0.5,
        'wontsee': -0.5
    }

    works = Counter()
    final_works = Counter()
    nb_ratings = {}
    c = 0
    neighbors = Counter()
    for her in Rating.objects.filter(work__in=my_rated_works.keys()).select_related('work', 'user'):
        c += 1
        neighbors[her.user.id] += values[my_rated_works[her.work.id]] * values[her.choice]

    score_of_neighbor = {}
    for user_id, score in neighbors.most_common(30 if category == 'manga' else 15):
        score_of_neighbor[user_id] = score

    bundle = Manga.objects.annotate(Count('rating')).filter(rating__count__gte=1).prefetch_related('rating_set').filter(rating__user__in=score_of_neighbor.keys())  # TODO : est-ce que ça regarde ceux qui y sont tous ?
    manga_ids = set(bundle.values_list('id', flat=True))

    works_by_id = {}
    for her in Rating.objects.filter(user__id__in=score_of_neighbor.keys()).exclude(choice__in=['willsee', 'wontsee']).select_related('work', 'user'):
        if not her.work.id in works_by_id:
            works_by_id[her.work.id] = her.work  # Adding for future retrieval
        is_manga = her.work.id in manga_ids
        if (is_manga and category == 'anime') or (not is_manga and category == 'manga'):
            continue
        if her.work.id not in works:
            works[her.work.id] = [values[her.choice], score]
            nb_ratings[her.work.id] = 1
        else:
            works[her.work.id][0] += values[her.choice]
            works[her.work.id][1] += score_of_neighbor[her.user.id]
            nb_ratings[her.work.id] += 1

    banned_works = set()
    for work_id in my_rated_works:
        banned_works.add(work_id)

    for i, work_id in enumerate(works):
        # Adding interesting works to the arena
        # Temporarily, a recommendation can be issued from one single user (beware of hentai)
        if (nb_ratings[work_id] > 1 or work_id in manga_ids) and work_id not in banned_works and works[work_id][0] > 0:
            final_works[(work_id, work_id in manga_ids)] = (float(works[work_id][0]) / nb_ratings[work_id], works[work_id][1])

    reco = []
    for (work_id, is_manga), _ in final_works.most_common(4):  # Retrieving top 4
        reco.append((works_by_id[work_id], is_manga))

    return reco
