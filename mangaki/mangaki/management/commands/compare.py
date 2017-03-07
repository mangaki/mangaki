import csv
import os.path
from collections import Counter

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split

from mangaki.utils.wals import MangakiWALS
from mangaki.utils.als import MangakiALS
from mangaki.utils.knn import MangakiKNN
from mangaki.utils.svd import MangakiSVD
from mangaki.utils.nmf import MangakiNMF

from mangaki.utils.values import rating_values
from mangaki.utils.zero import MangakiZero

import matplotlib.pyplot as plt

TEST_SIZE = 0.2
MODE = 'Movielens'
SUFFIX = '-ml' if MODE == 'Movielens' else ''


class Experiment(object):
    X = None
    y = None
    X_test = None
    y_test = None
    y_pred = None
    results = {}
    algos = None
    convert = None
    def __init__(self):
        # self.algos = [MangakiALS(20), MangakiWALS(20), MangakiSVD(20), MangakiKNN(20), MangakiZero()]
        self.algos = [MangakiNMF(20)]
        self.convert = (lambda x: float(x)) if MODE == 'Movielens' else lambda choice: rating_values[choice]
        self.make_dataset()
        self.execute()

    def clean_dataset(self):
        self.X = []
        self.y = []
        self.X_test = []
        self.y_test = []
        self.y_pred = []

    def make_dataset(self):
        self.clean_dataset()
        with open(os.path.join(settings.BASE_DIR, '../data/ratings%s.csv' % SUFFIX)) as f:
            ratings = [[int(line[0]), int(line[1]), line[2]] for line in csv.reader(f)]
        ratings = np.array(ratings, dtype=np.object)
        self.nb_users = max(ratings[:, 0]) + 1
        self.nb_works = max(ratings[:, 1]) + 1
        with open(os.path.join(settings.BASE_DIR, '../data/works%s.csv' % SUFFIX)) as f:
            self.works = [x for _, x in csv.reader(f)]
        train, test = train_test_split(ratings, random_state=0, test_size=TEST_SIZE)
        print('Train', train.shape)
        print('Test', test.shape)
        self.X = train[:, 0:2]
        self.y = [self.convert(choice) for choice in train[:, 2]]
        self.X_test = test[:, 0:2]
        self.y_test = [self.convert(choice) for choice in test[:, 2]]

    def execute(self):
        for algo in self.algos:
            print(algo)
            algo.set_parameters(self.nb_users, self.nb_works)
            # algo.load('backup.pickle')
            algo.fit(self.X, self.y)
            # algo.save('backup.pickle')
            self.y_pred = algo.predict(self.X_test)
            rmse = mean_squared_error(self.y_test, self.y_pred) ** 0.5
            print('RMSE', rmse)
            self.results.setdefault(algo.get_shortname(), []).append(rmse)

    def display_chart(self):
        handles = []
        for algo in self.algos:
            shortname = algo.get_shortname()
            curve, = plt.plot(self.results['x_axis'], self.results[shortname], label=str(algo), linewidth=1 if shortname == 'svd' else algo.NB_NEIGHBORS / 15, color='red' if shortname == 'svd' else 'blue')
            handles.append(curve)
        plt.legend(handles=handles)
        plt.show()


class Command(BaseCommand):
    args = ''
    help = 'Compare recommendation algorithms'

    def handle(self, *args, **options):
        experiment = Experiment()
