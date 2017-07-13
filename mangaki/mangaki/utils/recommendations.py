from collections import Counter
from mangaki.models import Rating, ColdStartRating, Work
from mangaki.utils.chrono import Chrono
from mangaki.utils.data import Dataset
from django.contrib.auth.models import User
from django.db.models import Count
from mangaki.utils.algo import ALGOS, fit_algo, get_algo_backup, get_dataset_backup
from mangaki.utils.algo import ALGOS, fit_algo
from mangaki.utils.ratings import current_user_ratings
from scipy.sparse import coo_matrix, vstack
from mangaki.utils.values import rating_values
import numpy as np
import pandas as pd
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


def get_reco_algo(request, algo_name='knn', category='all'):
    chrono = Chrono(is_enabled=CHRONO_ENABLED)
    dataset = Dataset()
    already_rated_works = list(current_user_ratings(request))
    if request.user.is_anonymous:
        assert request.user.id is None
        # We only support KNN for anonymous users, since the offline models did
        # not learn anything about them.
        # FIXME: We should also force KNN for new users for which we have no
        # offline trained model available.
        algo_name = 'knn'

    chrono.save('get rated works')

    if algo_name == 'knn':
        try:
            algo = get_algo_backup(algo_name)
            dataset = get_dataset_backup(algo_name)
        except FileNotFoundError:
            triplets = list(
                Rating.objects.values_list('user_id', 'work_id', 'choice'))
            chrono.save('get all %d interesting ratings' % len(triplets))
            dataset, algo = fit_algo(algo_name, triplets)
        framed_rated_works = pd.DataFrame(list(current_user_ratings(request).items()), columns=['work_id', 'choice'])
        framed_rated_works['work_id'] = dataset.encode_works(framed_rated_works['work_id'])
        framed_rated_works['rating'] = framed_rated_works['choice'].map(rating_values)
        ratings_from_user = coo_matrix((framed_rated_works['rating'],(np.zeros(len(framed_rated_works['work_id'])), framed_rated_works['work_id'])), shape=(1, algo.nb_works))
        ratings_from_user = ratings_from_user.tocsr()
        algo.M = vstack([algo.M, ratings_from_user])


        chrono.save('loading knn and expanding with current user ratings')


        encoded_neighbors = algo.get_neighbors([algo.nb_users]) # Now, current user ratings are in the last row of M
        neighbors = dataset.decode_users(encoded_neighbors[0])  # We only want for the first user

        chrono.save('get neighbors')

        # Only keep useful ratings for recommendation
        triplets = list(
            Rating.objects
                  .filter(user__id__in=neighbors + [request.user.id])
                  .exclude(choice__in=['willsee', 'wontsee'])
                  .values_list('user_id', 'work_id', 'choice')
        )
        if request.user.is_anonymous:
            triplets.extend([
                (request.user.id, work_id, choice)
                for work_id, choice in current_user_ratings(request).items()
                if choice not in ('willsee', 'wontsee')
            ])
        dataset, algo = fit_algo(algo_name, triplets)
    else:  # SVD or ALS, etc.
        try:
            algo = get_algo_backup(algo_name)
            dataset = get_dataset_backup(algo_name)
        except FileNotFoundError:
            # Every rating is useful
            triplets = list(
                Rating.objects.values_list('user_id', 'work_id', 'choice'))
            chrono.save('get all %d interesting ratings' % len(triplets))
            dataset, algo = fit_algo(algo_name, triplets)

    chrono.save('fit %s' % algo.get_shortname())

    if category != 'all':
        category_filter = set(Work.objects.filter(category__slug=category).values_list('id', flat=True))
    else:
        category_filter = dataset.interesting_works

    filtered_works = list((dataset.interesting_works & category_filter) - set(already_rated_works))

    chrono.save('remove already rated')

    pos_of_best = get_pos_of_best_works_for_user_via_algo(algo, dataset, request.user.id, filtered_works, limit=NB_RECO)
    best_work_ids = [filtered_works[pos] for pos in pos_of_best]

    chrono.save('compute every prediction')

    works = Work.objects.in_bulk(best_work_ids)
    # Some of the works may have been deleted since the algo backup was created.
    ranked_work_ids = [work_id for work_id in best_work_ids if work_id in works]

    chrono.save('get bulk')

    return {'work_ids': ranked_work_ids, 'works': works}
