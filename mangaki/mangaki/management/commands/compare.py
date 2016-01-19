from django.core.management.base import BaseCommand, CommandError
from sklearn.metrics import mean_squared_error
from sklearn import cross_validation
from mangaki.models import Rating, Work
from mangaki.utils.svd import MangakiSVD
from mangaki.utils.knn import MangakiKNN
from mangaki.utils.values import rating_values
import numpy as np
import matplotlib.pyplot as plt

PIG = 1
TRAIN_PIG_LENGTH = 10


class Experiment(object):
    X = None
    y = None
    X_test = None
    y_test = None
    y_pred = None
    results = {}
    algos = None
    def __init__(self, PIG):
        for TRAIN_PIG_LENGTH in range(10, 150, 20):
            print(TRAIN_PIG_LENGTH)
            self.algos = [MangakiSVD(), MangakiKNN(), MangakiKNN(30), MangakiKNN(45)]
            self.results.setdefault('x_axis', []).append(TRAIN_PIG_LENGTH)
            self.make_dataset(TRAIN_PIG_LENGTH)
            self.execute()

    def clean_dataset(self):
        self.X = []
        self.y = []
        self.X_test = []
        self.y_test = []
        self.y_pred = []

    def make_dataset(self, TRAIN_PIG_LENGTH):
        self.clean_dataset()
        c = 0
        for user_id, work_id, choice in Rating.objects.values_list('user_id', 'work_id', 'choice').order_by('work_id'):
            if user_id != PIG or c <= TRAIN_PIG_LENGTH:
                self.X.append((user_id, work_id))
                self.y.append(rating_values[choice])
                if user_id == PIG:
                    c += 1
            elif choice not in ['willsee', 'wontsee']:
                self.X_test.append((user_id, work_id))
                self.y_test.append(rating_values[choice])

    def execute(self):
        for algo in self.algos:#[MangakiSVD(), MangakiKNN(), MangakiKNN(30), MangakiKNN(42)]:
            print(algo)
            # algo.load('backup.pickle')
            algo.fit(self.X, self.y)
            # algo.save('backup.pickle')
            self.y_pred = algo.predict(self.X_test)
            rmse = mean_squared_error(self.y_test, self.y_pred) ** 0.5
            print('RMSE', rmse)
            self.results.setdefault(algo.get_shortname(), []).append(rmse)

    def display_ranking(self):
        work_titles = {}
        for work_id, work_title in Work.objects.values_list('id', 'title'):
            work_titles[work_id] = work_title

        for rank, i in enumerate(sorted(range(len(self.X_test)), key=lambda i: -self.y_pred[i]), start=1):
            _, work_id = self.X_test[i]
            print('%d. %s %f (was: %f)' % (rank, work_titles[work_id], self.y_pred[i], self.y_test[i]))

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
        experiment = Experiment(1)
        # experiment.display_ranking()
        experiment.display_chart()
