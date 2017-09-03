import os
import pickle
import random
from collections import Counter, namedtuple
from mangaki.utils.values import rating_values
import numpy as np
from datetime import datetime
from django.conf import settings
import csv


RATED_BY_AT_LEAST = 2


AnonymizedData = namedtuple('AnonymizedData', 'X y y_text nb_users nb_works')


class Dataset:
    def __init__(self):
        self.anonymized = None
        self.titles = None
        self.categories = None
        self.encode_user = None
        self.decode_user = None
        self.encode_work = None
        self.decode_work = None
        self.interesting_works = None
        self.datetime = datetime.now()

    def save(self, filename):
        with open(os.path.join(settings.PICKLE_DIR, filename), 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    def load(self, filename):
        with open(os.path.join(settings.PICKLE_DIR, filename), 'rb') as f:
            backup = pickle.load(f)
        self.anonymized = backup.anonymized
        self.titles = backup.titles
        self.categories = backup.categories
        self.encode_user = backup.encode_user
        self.decode_user = backup.decode_user
        self.encode_work = backup.encode_work
        self.decode_work = backup.decode_work
        self.interesting_works = backup.interesting_works

    def save_csv(self, suffix=''):
        ratings_path = os.path.join(settings.DATA_DIR, 'ratings{}.csv'.format(suffix))
        works_path = os.path.join(settings.DATA_DIR, 'works{}.csv'.format(suffix))
        confirm = True
        if os.path.isfile(ratings_path) or os.path.isfile(works_path):
            confirm = input('`{}` or `{}` already exists. Overwrite? [y/n] '
                            .format(ratings_path, works_path)) == 'y'
        if confirm:
            with open(ratings_path, 'w', newline='') as csvfile:
                data = csv.writer(csvfile, delimiter=',', quotechar='', quoting=csv.QUOTE_NONE)
                for (encoded_user_id, encoded_work_id), rating in zip(self.anonymized.X, self.anonymized.y_text):
                    data.writerow([encoded_user_id, encoded_work_id, rating])
            if self.titles and self.categories:
                with open(works_path, 'w', newline='') as csvfile:
                    data = csv.writer(csvfile, delimiter=',')
                    lines = []
                    for work_id, title in self.titles.items():
                        if work_id in self.encode_work:
                            lines.append([self.encode_work[work_id], title, self.categories[work_id]])
                    lines.sort()
                    for line in lines:
                        data.writerow(line)

    def load_csv(self, filename, convert=float, title_filename=None):
        with open(os.path.join(settings.DATA_DIR, filename)) as f:
            triplets = [[int(user_id), int(work_id), rating] for user_id, work_id, rating in csv.reader(f)]
        triplets = np.array(triplets, dtype=np.object)
        # noinspection PyTypeChecker
        vectorized_convert = np.vectorize(convert, otypes=[np.float64])
        self.anonymized = AnonymizedData(
            X=triplets[:, 0:2],
            y=vectorized_convert(triplets[:, 2]),
            y_text=triplets[:, 2],
            nb_users=max(triplets[:, 0]) + 1,
            nb_works=max(triplets[:, 1]) + 1
        )
        if title_filename is not None:
            with open(os.path.join(settings.DATA_DIR, title_filename)) as f:
                titles = []
                categories = []
                for line in csv.reader(f):
                    titles.append(line[1])
                    if len(line) > 2:
                        categories.append(line[2])
                self.titles = np.array(titles, dtype=np.object)
                self.categories = np.array(categories, dtype=np.object)

    def make_anonymous_data(self, triplets, convert=lambda choice: rating_values[choice], ordered=False):
        triplets = list(triplets)
        users = set()
        works = set()
        nb_ratings = Counter()
        X = []
        y = []
        y_text = []
        for user_id, work_id, rating in triplets:
            users.add(user_id)
            works.add(work_id)
            nb_ratings[work_id] += 1
        random.shuffle(triplets)  # Scramble time

        anonymous_u = list(range(len(users)))
        anonymous_w = list(range(len(works)))
        random.shuffle(anonymous_u)
        if ordered:
            works = sorted(works, key=lambda work_id: nb_ratings[work_id], reverse=True)
        else:
            random.shuffle(anonymous_w)
        encode_user = dict(zip(users, anonymous_u))
        encode_work = dict(zip(works, anonymous_w))
        decode_user = dict(zip(anonymous_u, users))
        decode_work = dict(zip(anonymous_w, works))

        interesting_works = set()
        for work_id, _ in nb_ratings.most_common():  # work_id values are sorted by decreasing number of ratings
            if nb_ratings[work_id] < RATED_BY_AT_LEAST:
                break
            interesting_works.add(work_id)

        for user_id, work_id, rating in triplets:
            X.append((encode_user[user_id], encode_work[work_id]))
            y.append(convert(rating))
            y_text.append(rating)

        self.anonymized = AnonymizedData(
            X=np.array(X),
            y=np.array(y),
            y_text=np.array(y_text),
            nb_users=len(users),
            nb_works=len(works)
        )

        self.encode_user = encode_user
        self.decode_user = decode_user
        self.encode_work = encode_work
        self.decode_work = decode_work
        self.interesting_works = interesting_works
        return self.anonymized

    def decode_users(self, encoded_user_ids):
        return [self.decode_user[encoded_user_id] for encoded_user_id in encoded_user_ids]

    def encode_works(self, work_ids):
        return [self.encode_work[work_id] for work_id in work_ids if work_id in self.encode_work]
