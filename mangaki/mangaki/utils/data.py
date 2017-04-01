import os
import pickle
import random
from collections import Counter, namedtuple
from mangaki.utils.values import rating_values
from mangaki.utils.common import PICKLE_DIR
import numpy as np
from datetime import datetime
from django.conf import settings
import csv


RATED_BY_AT_LEAST = 2


AnonymizedData = namedtuple('AnonymizedData', 'X y nb_users nb_works')


class Dataset:
    anonymized = None
    encode_user = None
    decode_user = None
    encode_work = None
    decode_work = None
    interesting_works = None
    def __init__(self):
        self.datetime = datetime.now()

    def save(self, filename):
        with open(os.path.join(PICKLE_DIR, filename), 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    def load(self, filename):
        with open(os.path.join(PICKLE_DIR, filename), 'rb') as f:
            backup = pickle.load(f)
        self.anonymized = backup.anonymized
        self.encode_user = backup.encode_user
        self.decode_user = backup.decode_user
        self.encode_work = backup.encode_work
        self.decode_work = backup.decode_work
        self.interesting_works = backup.interesting_works

    def load_csv(self, filename, convert=float):
        with open(os.path.join(settings.BASE_DIR, '../data', filename)) as f:
            triplets = [[int(user_id), int(work_id), convert(rating)] for user_id, work_id, rating in csv.reader(f)]
        triplets = np.array(triplets, dtype=np.object)
        self.anonymized = AnonymizedData(
            X=triplets[:, 0:2],
            y=triplets[:, 2],
            nb_users=max(triplets[:, 0]) + 1, 
            nb_works=max(triplets[:, 1]) + 1
        )

    def make_anonymous_data(self, queryset):
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

        self.anonymized = AnonymizedData(X=np.array(X), y=np.array(y), nb_users=len(users), nb_works=len(works))
        self.encode_user = encode_user
        self.decode_user = decode_user
        self.encode_work = encode_work
        self.decode_work = decode_work
        self.interesting_works = interesting_works
        return self.anonymized

    def decode_users(self, encoded_user_ids):
        return [self.decode_user[encoded_user_id] for encoded_user_id in encoded_user_ids]

    def encode_works(self, work_ids):
        return [self.encode_work[work_id] for work_id in work_ids]
