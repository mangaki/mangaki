# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from collections import Counter
import json
from sklearn import manifold
import pandas as pd
import numpy as np
import requests
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

    tsne = manifold.TSNE(n_components=2, init='pca', perplexity=5.0)
    X_tsne = tsne.fit_transform(M)
    
    Work = apps.get_model('mangaki', 'Work')
    items = Work.objects.in_bulk([algo.dataset.decode_work[i]
                                  for i in encoded_most_popular_items])
    
    user_points = []
    work_points = []
    for encoded_work_id, (x, y) in zip(encoded_most_popular_items,
                                       X_tsne[:NB_WORKS].astype(np.float64)):
        work_id = algo.dataset.decode_work[encoded_work_id]
        work_points.append({'work_id': work_id,
                            'title': items[work_id].title,
                            'poster': items[work_id].poster_url,
                            'x': x, 'y': y})
    
    with open(f'{settings.VIZ_ROOT}/{filename}', 'w') as f:
        f.write(json.dumps({'works': work_points, 'users': user_points}))


def get_2d_embeddings(algo_name):
    r = requests.get(f'{settings.VIZ_URL}/points-{algo_name}.json')
    return r.json()
