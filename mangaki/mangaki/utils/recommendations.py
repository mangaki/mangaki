from collections import Counter
from mangaki.models import Manga, Rating, Work
from django.contrib.auth.models import User
from django.db.models import Count

def get_recommendations(user, my_rated_works, category, editor):
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
    for her in Rating.objects.filter(work__in=my_rated_works.keys()):
        c += 1
        neighbors[her.user_id] += values[my_rated_works[her.work_id]] * values[her.choice]

    score_of_neighbor = {}
    for user_id, score in neighbors.most_common(30 if category == 'manga' else 15):
        score_of_neighbor[user_id] = score

    if editor == 'unspecified': 
        bundle = Manga.objects.values_list('id', flat=True)  # TODO : est-ce que ça regarde ceux qui y sont tous ?
        manga_ids = set(bundle)
    else:
        if editor == 'otototaifu':
            bundle = Manga.objects.filter(editor__in=['Ototo Manga','Taifu comics']).values_list('id', flat=True) 
            manga_ids = set(bundle)
        else:
            bundle = Manga.objects.filter(editor__icontains=editor).values_list('id', flat=True) 
            manga_ids = set(bundle)

    works_by_id = {}
    for her in Rating.objects.filter(user__id__in=score_of_neighbor.keys()).exclude(choice__in=['willsee', 'wontsee']):
        """if not her.work.id in works_by_id:
            works_by_id[her.work.id] = her.work  # Adding for future retrieval"""
        is_manga = her.work_id in manga_ids
        if (is_manga and category == 'anime') or (not is_manga and category == 'manga'):
            continue
        if her.work_id not in works:
            works[her.work_id] = [values[her.choice], score]
            nb_ratings[her.work_id] = 1
        else:
            works[her.work_id][0] += values[her.choice]
            works[her.work_id][1] += score_of_neighbor[her.user_id]
            nb_ratings[her.work_id] += 1

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
        reco.append((Work.objects.get(id=work_id), is_manga))

    return reco
