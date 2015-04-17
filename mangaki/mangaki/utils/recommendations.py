from collections import Counter
from mangaki.models import Rating


def get_recommendations(user, my_rated_works):
    values = {
        'like': 2,
        'dislike': -2,
        'neutral': 0.1,
        'willsee': 0.5,
        'wontsee': -0.5
    }

    works = Counter()
    nb_ratings = {}
    c = 0
    neighbors = Counter()
    for her in Rating.objects.filter(work__in=my_rated_works.keys()).select_related('work', 'user'):
        c += 1
        neighbors[her.user.id] += values[my_rated_works[her.work.id]] * values[her.choice]

    score_of_neighbor = {}
    for user_id, score in neighbors.most_common(10):
        score_of_neighbor[user_id] = score

    for her in Rating.objects.filter(user__id__in=score_of_neighbor.keys()).select_related('work', 'user'):
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

    for work_id in works:
        if nb_ratings[work_id] == 1 or work_id in banned_works:
            works[work_id] = (0, 0)
        else:
            works[work_id] = (float(works[work_id][0]) / nb_ratings[work_id], works[work_id][1])

    return works.most_common(4)
