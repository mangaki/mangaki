from django.core.management.base import BaseCommand, CommandError
from sklearn import cross_validation
from sklearn.metrics import mean_squared_error
from sklearn.cross_validation import train_test_split
from mangaki.utils.svd import MangakiSVD
from mangaki.utils.pca import MangakiPCA
from mangaki.utils.knn import MangakiKNN
from mangaki.utils.als import MangakiALS
from mangaki.utils.nmf import MangakiNMF
from mangaki.utils.zero import MangakiZero
from mangaki.utils.values import rating_values
from collections import Counter
import numpy as np
import random
import pandas
# import matplotlib.pyplot as plt

TEST_SIZE = 50000


class Experiment(object):
    X = None
    y = None
    X_test = None
    y_test = None
    y_pred = None
    results = {}
    algos = None
    def __init__(self, PIG_ID=None):
        self.algos = [MangakiNMF(30), MangakiALS(20), MangakiSVD(20), MangakiZero()]
        # self.results.setdefault('x_axis', []).append()
        self.make_dataset(PIG_ID)
        self.execute()

    def clean_dataset(self):
        self.X = []
        self.y = []
        self.X_test = []
        self.y_test = []
        self.y_pred = []

    def make_dataset(self, PIG_ID):
        self.clean_dataset()
        ratings = pandas.read_csv('data/ratings.csv', header=None).as_matrix()
        if PIG_ID:  # Let's focus on the PIG
            pig_ratings = {}
            for user_id, work_id, choice in ratings:
                if user_id == PIG_ID:
                    pig_ratings[work_id] = rating_values[choice]
        self.nb_users = max(ratings[:, 0]) + 1
        self.nb_works = max(ratings[:, 1]) + 1
        self.works = pandas.read_csv('data/works.csv', header=None).as_matrix()[:, 1]
        train, test = train_test_split(ratings, random_state=0, test_size=TEST_SIZE)
        if PIG_ID:
            train = ratings
        self.X = train[:, 0:2]
        self.y = list(map(lambda choice: rating_values[choice], train[:, 2]))
        self.X_test = test[:, 0:2]
        self.y_test = list(map(lambda choice: rating_values[choice], test[:, 2]))
        if PIG_ID:
            self.X_test = []
            self.y_test = []
            for work_id in range(self.nb_works):
                self.X_test.append((PIG_ID, work_id))
                self.y_test.append(0 if work_id not in pig_ratings else pig_ratings[work_id])
            self.X_test = np.asarray(self.X_test)
            self.y_test = np.asarray(self.y_test)

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

    def display_ranking(self):
        error = Counter()
        print(len(self.X_test))
        for rank, i in enumerate(sorted(range(len(self.X_test)), key=lambda i: -self.y_pred[i]), start=1):
            if True or rank <= 100 or rank >= 8338 or self.X_test[i][1] == 491:
                _, work_id = self.X_test[i]
                if self.y_test[i]:
                    print('%d. %s %f (was: %f)' % (rank, self.works[work_id], self.y_pred[i], self.y_test[i]))
                    error[(self.works[work_id], self.y_pred[i], self.y_test[i])] = mean_squared_error([self.y_pred[i]], [self.y_test[i]])
                else:
                    print('%d. %s %f' % (rank, self.works[work_id], self.y_pred[i]))
        print('Most deviated')
        for (title, pred, true), _ in error.most_common(50):
            if true < 0:
                print(title, pred, true)

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
        experiment = Experiment()  # 1706
        #experiment.display_ranking()
        # experiment.display_chart()
