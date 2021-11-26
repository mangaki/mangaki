# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

import numpy as np
import pandas as pd

from mangaki.models import Rating, Work
from mangaki.utils.fit_algo import fit_algo, get_algo_backup
from mangaki.utils.chrono import Chrono
from mangaki.utils.ratings import current_user_ratings, friend_ratings
from mangaki.utils.values import rating_values

NB_RECO = 10
CHRONO_ENABLED = True


def get_algo_backup_or_fit_knn(algo_name):
    try:
        algo = get_algo_backup(algo_name)
    except FileNotFoundError:
        triplets = list(
            Rating.objects.values_list('user_id', 'work_id', 'choice'))
        # In the future, we should warn the user it's gonna take a while
        algo_name = 'knn'
        algo = fit_algo('knn', triplets)
    return algo


def get_personalized_ranking(algo, user_id, work_ids, enc_rated_works=[],
                             ratings=[], limit=None):
    if user_id in algo.dataset.encode_user:
        encoded_user_id = algo.dataset.encode_user[user_id]
        X_test = np.asarray([[encoded_user_id,
                              algo.dataset.encode_work[work_id]]
                             for work_id in work_ids])
        y_pred = algo.predict(X_test)
    else:
        user_parameters = algo.fit_single_user(enc_rated_works, ratings)
        encoded_work_ids = [algo.dataset.encode_work[work_id]
                            for work_id in work_ids]
        y_pred = algo.predict_single_user(encoded_work_ids, user_parameters)

    # Get top work indices in decreasing value
    pos_of_best = y_pred.argsort()[::-1]
    if limit is not None:
        pos_of_best = pos_of_best[:limit]  # Up to some limit
    return pos_of_best


def get_reco_algo(request, algo_name='als', category='all'):
    chrono = Chrono(is_enabled=CHRONO_ENABLED)
    user_ratings = current_user_ratings(request)
    already_rated_works = list(user_ratings)

    chrono.save('get rated works')

    algo = get_algo_backup_or_fit_knn(algo_name)

    available_works = set(algo.dataset.encode_work.keys())
    df_rated_works = (pd.DataFrame(list(user_ratings.items()),
                                   columns=['work_id', 'choice'])
                        .query('work_id in @available_works'))
    enc_rated_works = df_rated_works['work_id'].map(algo.dataset.encode_work)
    user_rating_values = df_rated_works['choice'].map(rating_values)

    # User gave the same rating to all works considered in the reco
    if algo_name == 'als' and len(set(user_rating_values)) == 1:
        algo = get_algo_backup_or_fit_knn('knn')

    chrono.save('retrieve or fit %s' % algo.get_shortname())

    category_filter = algo.dataset.interesting_works
    if category != 'all':
        category_filter &= set(Work.objects.filter(category__slug=category)
                                           .values_list('id', flat=True))

    filtered_works = list((algo.dataset.interesting_works & category_filter) -
                          set(already_rated_works))
    chrono.save('remove already rated, left {:d}'.format(len(filtered_works)))

    pos_of_best = get_personalized_ranking(algo, request.user.id,
                                           filtered_works, enc_rated_works,
                                           user_rating_values, limit=NB_RECO)
    best_work_ids = [filtered_works[pos] for pos in pos_of_best]

    chrono.save('compute every prediction')

    works = Work.objects.in_bulk(best_work_ids)
    # Some of the works may have been deleted since the algo backup was created
    ranked_work_ids = [work_id for work_id in best_work_ids
                       if work_id in works]

    chrono.save('get bulk')

    return {'work_ids': ranked_work_ids, 'works': works}


def get_group_reco_algo(request, users_id=None, algo_name='als',
                        category='all'):
    # users_id contain a group to recommend to
    # It should include the current user, which can't be anonymous
    if request.user.is_anonymous:
        get_reco_algo(request, algo_name, category)
    if users_id is None:
        users_id = [request.user.id]
    elif request.user.id not in users_id:
        users_id.append(request.user.id)

    chrono = Chrono(is_enabled=CHRONO_ENABLED)

    user_ratings = {}
    tmp = []
    for user_id in users_id:
        ratings = friend_ratings(request, user_id)
        # Ignore users with no ratings
        if len(ratings) > 0:
            user_ratings[user_id] = ratings
            tmp.append(user_id)
    user_id = tmp

    # What is already rated for a group? intersection or union of seen works?
    already_rated_works = list(set().union(*[
        set(ratings) for ratings in user_ratings.values()
    ]))

    chrono.save('get rated works')

    algo = get_algo_backup_or_fit_knn(algo_name)

    # # One user gave the same rating to all works considered in the reco
    # # It may make sense to only use knn for this user, and not all
    # for user_rating_values in users_rating_values:
    #     if algo_name == 'als' and len(set(user_rating_values)) == 1:
    #         algo = get_algo_backup_or_fit_knn('knn')
    #         break

    chrono.save('retrieve or fit %s' % algo.get_shortname())

    category_filter = algo.dataset.interesting_works
    if category != 'all':
        category_filter &= set(Work.objects.filter(category__slug=category)
                                           .values_list('id', flat=True))

    filtered_works = list((algo.dataset.interesting_works & category_filter) -
                          set(already_rated_works))
    chrono.save('remove already rated, left {:d}'.format(len(filtered_works)))

    encoded_work_ids = [algo.dataset.encode_work[work_id]
                        for work_id in filtered_works]

    encoded_user_ids = []
    extra_users_parameters = []
    available_works = None
    for user_id in users_id:
        # TODO: also recompute parameters if ratings have changed
        if user_id not in algo.dataset.encode_user:
            if available_works is None:
                available_works = set(algo.dataset.encode_work.keys())
            df_rated_works = (pd.DataFrame(list(user_ratings[user_id].items()),
                                           columns=['work_id', 'choice'])
                                .query('work_id in @available_works'))
            enc_rated_works = df_rated_works['work_id'].map(
                algo.dataset.encode_work
            )
            user_rating_values = df_rated_works['choice'].map(rating_values)
            extra_users_parameters.append(algo.fit_single_user(
                enc_rated_works,
                user_rating_values
            ))
        else:
            encoded_user_ids.append(algo.dataset.encode_user[user_id])

    pos_of_best = algo.recommend(encoded_user_ids,
                                 extra_users_parameters=extra_users_parameters,
                                 item_ids=encoded_work_ids,
                                 k=NB_RECO)['item_id']
    best_work_ids = [filtered_works[pos] for pos in pos_of_best]

    chrono.save('compute every prediction')

    works = Work.objects.in_bulk(best_work_ids)
    # Some of the works may have been deleted since the algo backup was created
    ranked_work_ids = [work_id for work_id in best_work_ids
                       if work_id in works]

    chrono.save('get bulk')

    return {'work_ids': ranked_work_ids, 'works': works}
