# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from collections import Counter
import json
from sklearn import manifold
import pandas as pd
import numpy as np
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from mangaki.utils.values import rating_values


def dump_2d_embeddings(algo, filename, N=2025):
    item_ids = Counter(algo.dataset.anonymized.X[:, 1])
    encoded_most_popular_items = np.array(item_ids.most_common(N))[:, 0]
    metaencoding = dict(zip(encoded_most_popular_items, range(N)))

    user_ids = Counter(algo.dataset.anonymized.X[:, 0])
    encoded_most_active_users = np.array(user_ids.most_common(N))[:, 0]

    NB_WORKS = len(encoded_most_popular_items)  # Currently equal to N
    NB_USERS = len(encoded_most_active_users)
    
    M = algo.VT.T[encoded_most_popular_items]

    tsne = manifold.TSNE(n_components=2, init='pca')
    X_tsne = tsne.fit_transform(M)
    
    Work = apps.get_model('mangaki', 'Work')
    items = Work.objects.in_bulk([algo.dataset.decode_work[i]
                                  for i in encoded_most_popular_items])
    
    user_points = []
    work_points = []
    for encoded_work_id, (x, y) in zip(encoded_most_popular_items,
                                       X_tsne[:NB_WORKS].astype(np.float64)):
        work_id = algo.dataset.decode_work[encoded_work_id]
        work_points.append({'title': items[work_id].title,
                            'poster': items[work_id].poster_url,
                            'x': x, 'y': y})

    """
    usernames = ['jj', 'Tomoko', 'Akulen']
    df = pd.DataFrame(
        Rating.objects.filter(user__username__in=usernames).values_list(
        'user__id', 'work_id', 'choice'),
        columns=('user_id', 'work_id', 'choice'))
    # Replace with friend_ratings
    user_ids = df['user_id'].unique().tolist()
    users = User.objects.in_bulk(user_ids)  # Get usernames for display
    df['rating'] = df['choice'].map(rating_values)
    df['encoded_work_id'] = df['work_id'].map(algo.dataset.encode_work)
    df['metacode'] = df['encoded_work_id'].map(metaencoding)
    for user_id in user_ids:
        this_user = df.query('user_id == @user_id and choice == "favorite" and '
                             'encoded_work_id in @encoded_most_popular_items')
        user_ratings = np.array(this_user['rating'])[:, None]
        rated_works_pos = np.array(this_user['metacode']).astype(int)
        x, y = ((user_ratings * X_tsne[rated_works_pos]).sum(axis=0) /
                this_user['rating'].sum()).tolist()
        user_points.append({'title': f'{users[user_id].username}',
                            'x': x, 'y': y})
    """
    
    with open(f'{settings.VIZ_ROOT}/{filename}', 'w') as f:
        f.write(json.dumps({'works': work_points, 'users': user_points}))
