# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

import numpy as np
import pandas as pd

from mangaki.models import Rating, Work
from mangaki.utils.fit_algo import fit_algo, get_algo_backup
from mangaki.utils.chrono import Chrono
from mangaki.utils.ratings import current_user_ratings, friend_ratings
from mangaki.utils.values import rating_values
from mangaki.utils.crypto import HomomorphicEncryption

NB_RECO = 10
CHRONO_ENABLED = True


def get_algo_backup_or_fit_svd(algo_name):
    try:
        algo = get_algo_backup(algo_name)
    except FileNotFoundError:
        # Fallback to SVD
        triplets = list(
            Rating.objects.values_list('user_id', 'work_id', 'choice'))
        algo_name = 'svd'
        algo = fit_algo('svd', triplets)
    return algo


def get_group_reco_algo(request, users_id=None, algo_name='als',
                        category='all', merge_type=None):
    # others_id contain a group to recommend to
    others_id = users_id
    if request.user.is_anonymous or users_id is None:
        others_id = []
    elif request.user.id in users_id:
        others_id = [user_id for user_id in users_id
                     if user_id != request.user.id]

    chrono = Chrono(is_enabled=CHRONO_ENABLED)

    algo = get_algo_backup_or_fit_svd(algo_name)
    available_works = set(algo.dataset.encode_work.keys())

    chrono.save('retrieve or fit %s' % algo.get_shortname())

    # Building the training set
    my_ratings = current_user_ratings(request)  # Myself

    if not request.user.is_anonymous and others_id:
        triplets = friend_ratings(request, others_id)
        df = pd.DataFrame(triplets, columns=['user_id', 'work_id', 'choice']).query(
            'work_id in @available_works')
        df['encoded_work_id'] = df['work_id'].map(
            algo.dataset.encode_work)
        df['rating'] = df['choice'].map(rating_values)
        # Ignore those with no ratings in the group
        participating_other_ids = df['user_id'].unique().tolist()
    else:
        participating_other_ids = []
    group_length = 1 + len(participating_other_ids)

    # What is already rated for a group? intersection or union of seen works?
    # Here we default with intersection
    merge_function = \
        set.union if merge_type == 'union' else set.intersection
    sets_of_rated_works = [set(my_ratings.keys())]
    if merge_type != 'mine':
        for user_id in participating_other_ids:
            sets_of_rated_works.append(set(
                df.query('user_id == @user_id')['work_id'].tolist()))
    already_rated_works = list(merge_function(*sets_of_rated_works))

    chrono.save('get rated works')

    category_filter = algo.dataset.interesting_works
    if category != 'all':
        category_filter &= set(Work.objects.filter(category__slug=category)
                                           .values_list('id', flat=True))

    filtered_works = list((algo.dataset.interesting_works & category_filter) -
                          set(already_rated_works))
    chrono.save('remove already rated, left {:d}'.format(len(filtered_works)))

    encoded_work_ids = [algo.dataset.encode_work[work_id]
                        for work_id in filtered_works]

    my_mean, my_feat = algo.fit_single_user(
        [algo.dataset.encode_work[work_id] for work_id in my_ratings.keys()],
        [rating_values[choice] for choice in my_ratings.values()]
    )

    if algo.get_shortname().startswith('svd') and participating_other_ids:
        he = HomomorphicEncryption(participating_other_ids, quantize_round=1,
                                   MAX_VALUE=800 * group_length)
        transform = he.encrypt_embeddings
        is_encrypted = True
    else:
        transform = lambda _, parameters: parameters  # Return the embeddings
        is_encrypted = False

    embeddings = []
    for user_id in participating_other_ids:
        user_ratings = df.query("user_id == @user_id")
        embeddings.append(transform(user_id,
            algo.fit_single_user(
                user_ratings['encoded_work_id'],
                user_ratings['rating']
            )))

    if is_encrypted:
        sum_means, sum_feats = he.decrypt_embeddings(embeddings)
        group_parameters = [[(my_mean + sum_means) / group_length,
                             (my_feat + sum_feats) / group_length]]
    else:
        group_parameters = [(my_mean, my_feat)] + embeddings

    pos_of_best = algo.recommend(user_ids=[],  # Anonymous & retrained
                                 extra_users_parameters=group_parameters,
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
