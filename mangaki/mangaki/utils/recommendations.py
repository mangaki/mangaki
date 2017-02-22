from collections import Counter
from mangaki.models import Rating, ColdStartRating, Work
from mangaki.utils.chrono import Chrono
from mangaki.utils.values import rating_values, rating_values_dpp
from django.contrib.auth.models import User
from django.db.models import Count
from django.db import connection
import random
from datetime import datetime
from mangaki.utils.wals import MangakiWALS
from mangaki.utils.als import MangakiALS
from mangaki.utils.knn import MangakiKNN
from mangaki.utils.svd import MangakiSVD
import numpy as np
import pickle
import json
import os.path


NB_NEIGHBORS = 20
NB_RECO = 10
RATED_BY_AT_LEAST = 2
CHRONO_ENABLED = False
ALGOS = {
    'knn': lambda: MangakiKNN(NB_NEIGHBORS),
    'svd': lambda: MangakiSVD(20),
    'als': lambda: MangakiALS(20),
    'wals': lambda: MangakiWALS(20),
}


def make_anonymous_data(queryset):
    triplets = []
    users = set()
    works = set()
    nb_ratings = Counter()
    X = []
    y = []
    for user_id, work_id, rating in queryset.values_list('user_id', 'work_id', 'choice'):
        users.add(user_id)
        works.add(work_id)
        triplets.append((user_id, work_id, rating))
        nb_ratings[work_id] += 1
    random.shuffle(triplets)  # Scramble time

    anonymous_u = list(range(len(users)))
    anonymous_w = list(range(len(works)))
    random.shuffle(anonymous_u)
    random.shuffle(anonymous_w)
    encode_user = dict(zip(users, anonymous_u))
    encode_work = dict(zip(works, anonymous_w))
    decode_user = dict(zip(anonymous_u, users))
    decode_work = dict(zip(anonymous_w, works))

    interesting_works = set()
    for work_id, _ in nb_ratings.most_common():  # work_id are sorted by decreasing number of ratings
        if nb_ratings[work_id] < RATED_BY_AT_LEAST:
            break
        interesting_works.add(work_id)

    for user_id, work_id, rating in triplets:
        X.append((encode_user[user_id], encode_work[work_id]))
        y.append(rating_values[rating])
    return np.array(X), np.array(y), len(users), len(works), encode_user, decode_user, encode_work, decode_work, interesting_works


def get_reco_algo(user, algo_name='knn', category='all'):
    chrono = Chrono(CHRONO_ENABLED)

    already_rated_works = Rating.objects.filter(user=user).values_list('work_id', flat=True)

    chrono.save('[%dQ] get rated works' % len(connection.queries))

    if algo_name == 'knn':
        queryset = Rating.objects.filter(work__in=already_rated_works)
        ratings_pack = make_anonymous_data(queryset)

        chrono.save('[%dQ] make first anonymous data' % len(connection.queries))

        X, y, nb_users, nb_works, encode_user, decode_user, encode_work, decode_work, interesting_works = ratings_pack
        algo = MangakiKNN(NB_NEIGHBORS)
        algo.set_parameters(nb_users, nb_works)
        algo.fit(X, y)

        chrono.save('[%dQ] prepare first fit' % len(connection.queries))

        encoded_neighbors = algo.get_neighbors([encode_user[user.id]])[0]
        neighbors = [decode_user[encoded_user_id] for encoded_user_id in encoded_neighbors]

        chrono.save('[%dQ] get neighbors (checksum: %d)' % (len(connection.queries), sum(neighbors)))

        queryset = Rating.objects.filter(user__id__in=neighbors + [user.id]).exclude(choice__in=['willsee', 'wontsee'])
    else:
        queryset = Rating.objects.all()

    chrono.save('[%dQ] get interesting %d ratings' % (len(connection.queries), queryset.count()))

    filename = 'ratings.pickle'
    if algo_name == 'knn' or not os.path.isfile('ratings.pickle'):
        ratings_pack = make_anonymous_data(queryset)
        if algo_name != 'knn':
            with open(filename, 'wb') as f:
                pickle.dump(ratings_pack, f, pickle.HIGHEST_PROTOCOL)
    else:
        with open(filename, 'rb') as f:
            ratings_pack = pickle.load(f)
    X, y, nb_users, nb_works, encode_user, decode_user, encode_work, decode_work, interesting_works = ratings_pack

    chrono.save('[%dQ] get all %d interesting ratings' % (len(connection.queries), queryset.count()))

    algo = ALGOS[algo_name]()
    algo.set_parameters(nb_users, nb_works)

    backup_filename = '%s-%s.pickle' % (algo.get_shortname(), datetime.strftime(datetime.now(), '%Y%m%d'))
    if os.path.isfile(backup_filename):
        algo.load(backup_filename)
    else:
        algo.fit(X, y)
        if algo_name in {'svd', 'als', 'wals'}:
            algo.save(backup_filename)

    chrono.save('[%dQ] fit %s' % (len(connection.queries), algo.get_shortname()))

    if category != 'all':
        category_filter = set(Work.objects.filter(category__slug=category).values_list('id', flat=True))
    else:
        category_filter = interesting_works

    filtered_works = (interesting_works & category_filter) - set(already_rated_works)
    encoded_works = [encode_work.get(work_id) for work_id in filtered_works]
    nb_test = len(encoded_works)

    chrono.save('[%dQ] remove already rated' % len(connection.queries))

    X_test = list(zip([encode_user[user.id]] * nb_test, encoded_works))
    X_test = np.asarray(X_test)
    y_pred = algo.predict(X_test)
    pos = y_pred.argsort()[-NB_RECO:][::-1]  # Get top NB_RECO work indices in decreasing value

    chrono.save('[%dQ] compute everything' % len(connection.queries))

    best_work_ids = [decode_work[work_id] for _, work_id in X_test[pos]]
    works = Work.objects.in_bulk(best_work_ids)

    chrono.save('[%dQ] get bulk' % len(connection.queries))

    return {'work_ids': best_work_ids, 'works': works}
