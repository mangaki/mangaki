from django.conf import settings
from django.core.management.base import BaseCommand

from collections import defaultdict
from sklearn.model_selection import ShuffleSplit
import numpy as np
import csv
import os.path

from mangaki.utils.data import Dataset
from mangaki.utils.wals import MangakiWALS
from mangaki.utils.als import MangakiALS
from mangaki.utils.knn import MangakiKNN
from mangaki.utils.svd import MangakiSVD
from mangaki.utils.pca import MangakiPCA
from mangaki.utils.zero import MangakiZero
from mangaki.utils.values import rating_values
import logging


NB_SPLIT = 5  # Divide the dataset into 5 buckets
FILENAMES = {
    'movies': 'ratings-ml.csv',
    'mangas': 'ratings.csv'
}
CONVERT_FUNCTIONS = {
    'movies': float,
    'mangas': lambda choice: rating_values[choice]
}

logger = logging.getLogger(__name__)


class Experiment(object):
    def __init__(self, dataset_name):
        self.algos = [
            # lambda: MangakiALS(10),
            lambda: MangakiALS(20),
            # lambda: MangakiALS(30),
            # lambda: MangakiALS(40),
            lambda: MangakiWALS(20),
            # lambda: MangakiSVD(10),
            lambda: MangakiSVD(20),
            # lambda: MangakiSVD(30),
            # lambda: MangakiSVD(40),
            # lambda: MangakiSVD(50),
            # lambda: MangakiPCA(20),
            lambda: MangakiKNN(20),
            # lambda: MangakiKNN(40),
            lambda: MangakiZero()
        ]
        self.anonymized = None
        self.load_dataset(dataset_name)

    def load_dataset(self, dataset_name):
        dataset = Dataset()
        dataset.load_csv(
            FILENAMES.get(dataset_name, FILENAMES['mangas']),
            CONVERT_FUNCTIONS.get(dataset_name, CONVERT_FUNCTIONS['mangas'])
        )
        self.anonymized = dataset.anonymized

    def compare_models(self):
        k_fold = ShuffleSplit(n_splits=NB_SPLIT)
        rmse_values = defaultdict(list)
        for i_train, i_test in k_fold.split(self.anonymized.X):
            for algo in self.algos:
                model = algo()
                logger.info('-> Computing', model.get_shortname())
                model.set_parameters(self.anonymized.nb_users, self.anonymized.nb_works)
                model.fit(self.anonymized.X[i_train], self.anonymized.y[i_train])
                y_pred = model.predict(self.anonymized.X[i_test])
                rmse = model.compute_rmse(y_pred, self.anonymized.y[i_test])
                if model.verbose:
                    logger.debug('Predicted: %s' % y_pred[:5])
                    logger.debug('Was: %s' % self.anonymized.y[i_test][:5])
                logger.debug('RMSE %.3f' % rmse)
                rmse_values[model.get_shortname()].append(rmse)
                logger.debug('')
        logger.info('# Final results')
        for algo_name in rmse_values:
            logger.info('%s: RMSE = %.3f' % (algo_name, np.mean(rmse_values[algo_name])))


class Command(BaseCommand):
    args = ''
    help = 'Compare recommendation algorithms'

    def add_arguments(self, parser):
        parser.add_argument('dataset_name', type=str)

    def handle(self, *args, **options):
        dataset_name = options.get('dataset_name')
        experiment = Experiment(dataset_name)
        experiment.compare_models()
