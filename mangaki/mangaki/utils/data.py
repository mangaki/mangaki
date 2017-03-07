import os
import pickle
import random
from collections import Counter, namedtuple
from mangaki.utils.values import rating_values
import numpy as np
from datetime import datetime
import csv


RATED_BY_AT_LEAST = 2
MOVIELENS_FOLDER = 'ml-latest-small'


AnonymizedData = namedtuple('AnonymizedData', 'X y nb_users nb_works')


class Dataset:
    datetime = None
    source = None
    anonymized = None
    encode_user = None
    decode_user = None
    encode_work = None
    decode_work = None
    interesting_works = None
    def __init__(self):
        self.datetime = datetime.now()

    def save(self, filename):
        with open(os.path.join('pickles', filename), 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    def load(self, filename):
        with open(os.path.join('pickles', filename), 'rb') as f:
            backup = pickle.load(f)
        self.anonymized = backup.anonymized
        self.encode_user = backup.encode_user
        self.decode_user = backup.decode_user
        self.encode_work = backup.encode_work
        self.decode_work = backup.decode_work
        self.interesting_works = backup.interesting_works

    def save_csv(self, filename):
        works = set()
        with open(os.path.join('data', 'ratings-ml.csv'), 'w') as csvfile:
            writer = csv.writer(csvfile)
            for (user_id, work_id), rating in zip(self.anonymized.X, self.anonymized.y):
                works.add(work_id)
                writer.writerow([user_id, work_id, rating])
        title_of = {}
        tags_of = {}
        with open(os.path.join('data', MOVIELENS_FOLDER, 'movies.csv'), 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            for row in reader:
                work_id, title, tags = row[:3]
                title_of[work_id] = title
                tags_of[work_id] = tags
        with open(os.path.join('data', 'works-ml.csv'), 'w') as works_csv:
            with open(os.path.join('data', 'tags-ml.csv'), 'w') as tags_csv:
                works_w = csv.writer(works_csv)
                tags_w = csv.writer(tags_csv)
                for work_id in sorted(works):
                    works_w.writerow([work_id, title_of[self.decode_work[work_id]]])
                    tags_w.writerow([work_id, tags_of[self.decode_work[work_id]]])

    def get_data_from_movielens(self):
        self.source = 'Movielens'
        triplets = []
        users = set()
        works = set()
        nb_ratings = Counter()
        with open(os.path.join('data', MOVIELENS_FOLDER, 'ratings.csv'), 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            for row in reader:
                user_id, work_id, rating = row[:3]
                users.add(user_id)
                works.add(work_id)
                triplets.append((user_id, work_id, rating))
                nb_ratings[work_id] += 1
        # random.shuffle(triplets)
        return triplets, users, works, nb_ratings

    def get_data_from_queryset(self, queryset):
        self.source = 'Mangaki'
        triplets = []
        users = set()
        works = set()
        nb_ratings = Counter()
        for user_id, work_id, rating in queryset.values_list('user_id', 'work_id', 'choice'):
            users.add(user_id)
            works.add(work_id)
            triplets.append((user_id, work_id, rating))
            nb_ratings[work_id] += 1
        random.shuffle(triplets)  # Scramble time
        return triplets, users, works, nb_ratings

    def make_anonymous_data(self, triplets, users, works, nb_ratings):
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

        X = []
        y = []
        for user_id, work_id, rating in triplets:
            X.append((encode_user[user_id], encode_work[work_id]))
            y.append(rating_values[rating] if self.source == 'Mangaki' else rating)

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
