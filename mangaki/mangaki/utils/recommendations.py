from collections import Counter
from mangaki.models import Rating, ColdStartRating, Work
from mangaki.utils.chrono import Chrono
from mangaki.utils.data import Dataset
from django.contrib.auth.models import User
from django.db.models import Count
from mangaki.utils.algo import ALGOS, fit_algo, get_algo_backup, get_dataset_backup
import numpy as np
import json
import os.path


NB_RECO = 10
CHRONO_ENABLED = True


def user_exists_in_backup(user, algo_name):
    try:
        dataset = get_dataset_backup(algo_name)
        return user.id in dataset.encode_user
    except FileNotFoundError:
        return False


def get_pos_of_best_works_for_user_via_algo(algo, dataset, user_id, work_ids, limit=None):
    encoded_user_id = dataset.encode_user[user_id]
    encoded_works = dataset.encode_works(work_ids)
    X_test = np.asarray([[encoded_user_id, encoded_work_id] for encoded_work_id in encoded_works])
    y_pred = algo.predict(X_test)
    pos_of_best = y_pred.argsort()[::-1]  # Get top work indices in decreasing value
    if limit is not None:
        pos_of_best = pos_of_best[:limit]  # Up to some limit
    return pos_of_best


def get_reco_algo(user, algo_name='knn', category='all'):
    chrono = Chrono(is_enabled=CHRONO_ENABLED)

    already_rated_works = Rating.objects.filter(user=user).values_list('work_id', flat=True)

    chrono.save('get rated works')

    if algo_name == 'knn':
        queryset = Rating.objects.filter(work__in=already_rated_works)
        dataset = Dataset()
        anonymized = dataset.make_anonymous_data(queryset)

        chrono.save('make first anonymous data')

        algo = ALGOS['knn']()
        algo.set_parameters(anonymized.nb_users, anonymized.nb_works)
        algo.fit(anonymized.X, anonymized.y)

        chrono.save('prepare first fit')

        encoded_neighbors = algo.get_neighbors([dataset.encode_user[user.id]])
        neighbors = dataset.decode_users(encoded_neighbors[0])  # We only want for the first user

        chrono.save('get neighbors')

        # Only keep useful ratings for recommendation
        queryset = Rating.objects.filter(user__id__in=neighbors + [user.id]).exclude(choice__in=['willsee', 'wontsee'])
    else:
        # Every rating is useful
        queryset = Rating.objects.all()

    chrono.save('get all %d interesting ratings' % queryset.count())

    dataset = Dataset()
    try:
        algo = get_algo_backup(algo_name)
        dataset = get_dataset_backup(algo_name)
    except FileNotFoundError:
        dataset, algo = fit_algo(algo_name, queryset, algo.get_backup_filename())

    chrono.save('fit %s' % algo.get_shortname())

    if category != 'all':
        category_filter = set(Work.objects.filter(category__slug=category).values_list('id', flat=True))
    else:
        category_filter = dataset.interesting_works

    filtered_works = list((dataset.interesting_works & category_filter) - set(already_rated_works))

    chrono.save('remove already rated')

    pos_of_best = get_pos_of_best_works_for_user_via_algo(algo, dataset, user.id, filtered_works, limit=NB_RECO)
    best_work_ids = [filtered_works[pos] for pos in pos_of_best]

    chrono.save('compute every prediction')

    works = Work.objects.in_bulk(best_work_ids)

    chrono.save('get bulk')

    return {'work_ids': best_work_ids, 'works': works}
