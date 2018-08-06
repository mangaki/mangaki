import json
import logging
import os.path
from datetime import datetime
from collections import defaultdict
from typing import Type, List, Any, Dict, Optional

import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand
from sklearn.model_selection import ShuffleSplit

import mangaki.utils.logging as mangaki_logging
from mangaki.settings import DATA_DIR, TEST_DATA_DIR
from mangaki.algo import Dataset
from mangaki.algo import RecommendationAlgorithm
from mangaki.utils.values import rating_values

FILENAMES = {
    'movies': 'ratings-ml.csv',
    'mangas': 'ratings.csv',
    'dummy': os.path.join(TEST_DATA_DIR, 'ratings.csv'),
    'balse': 'balse/ratings.csv'
}
CONVERT_FUNCTIONS = {
    'movies': float,
    'mangas': lambda choice: rating_values[choice]
}

EXPERIMENTS_FOLDER = os.path.join(DATA_DIR, 'experiments')
DEFAULT_CONFIG_FILENAME = os.path.join(EXPERIMENTS_FOLDER, 'default.json')

logger = logging.getLogger(__name__)


class AlgorithmWrapper:
    def __init__(self, short_name: str, klass: Type[RecommendationAlgorithm],
                 args: Optional[List[Any]] = None,
                 kwargs: Optional[Dict[str, Any]] = None):
        self.klass = klass
        self.short_name = short_name
        self.args = args or []
        self.kwargs = kwargs or {}

    def make_instance(self) -> RecommendationAlgorithm:
        return self.klass(*self.args, **self.kwargs)


class Experiment(object):
    def __init__(self, dataset_name, eval_metrics, experiment_filename=None,
                 fancy_formatting: bool = False):
        self.algos = []

        self.experiment_filename = experiment_filename
        if experiment_filename:
            self.prepare_experiment()

        self.evaluation_metrics = eval_metrics
        self.anonymized = None
        self.fancy_formatting = fancy_formatting
        self.load_dataset(dataset_name)

    def prepare_experiment(self):
        """
        Prepare the experiment.

        The algorithms are registered under their short name, which can be found in their definition file (e.g. als.py).

        Read the configuration for the experiment as a (short_name, …params) tuple.
        Wrap configuration in an AlgorithmWrapper which will create instance during comparisons.

        Populate the `self.algos` list with wrappers.

        May raise ValueError or KeyError if the experiment file is malformed or invalid.
        Also, if the algorithms does not exist (import failure).

        Returns: None.

        """
        with open(self.experiment_filename, 'r') as f:
            experiment_data = json.loads(f.read())

        configurations = experiment_data['configurations']
        for config in configurations:
            short_name, *params = config
            klass = RecommendationAlgorithm.factory.algorithm_registry[short_name]
            self.algos.append(AlgorithmWrapper(short_name, klass, params))

    def load_dataset(self, dataset_name):
        dataset = Dataset()
        dataset.load_csv(
            FILENAMES.get(dataset_name, FILENAMES['mangas']),
            CONVERT_FUNCTIONS.get(dataset_name, CONVERT_FUNCTIONS['mangas'])
        )
        self.anonymized = dataset.anonymized

    def compute_metrics(self, model, y_pred, i_test):
        results = {}
        for metric in self.evaluation_metrics:
            compute_method = getattr(model, 'compute_{}'.format(metric))
            results[metric] = compute_method(y_pred, self.anonymized.y[i_test])
            logger.debug('{} ({}) {:f}'.format(metric,
                                               i_test,
                                               results[metric]))

        return results

    def format_final_result(self, algo_name: str, results: List[float]):
        # noinspection PyTypeChecker
        mean = float(np.mean(results))
        # noinspection PyTypeChecker
        var = float(np.var(results))
        std = 1.96 * np.sqrt(var / len(results))

        if self.fancy_formatting:
            return '[{}] {:5f} ± {:5f}'.format(
                algo_name,
                round(mean, 6),
                round(std, 6)
            )

        else:
            return '[{}] mean={:f} var={:f} std={:f}'.format(
                algo_name,
                mean,
                var,
                std
            )

    def compare_models(self, nb_split: int, full_cv: bool):
        if not self.algos:
            logger.warning('No algorithms has been specified in this experiment. Stopping early!'
                           'Did you forget an experiment file with -exp?')
            return

        k_fold = ShuffleSplit(n_splits=nb_split)
        metrics = defaultdict(lambda: defaultdict(list))

        for pass_index, (i_train, i_test) in enumerate(k_fold.split(self.anonymized.X), start=1):
            X_train = self.anonymized.X[i_train]
            y_train = self.anonymized.y[i_train]
            X_test = self.anonymized.X[i_test]
            y_test = self.anonymized.y[i_test]
            print(y_train[:5], y_test[:5])
            df_train = pd.DataFrame(np.column_stack((X_train, y_train)), columns=['user_id', 'work_id', 'rating'], dtype=float)
            print(df_train.head())
            df_test = pd.DataFrame(np.column_stack((X_test, y_test)), columns=['user_id', 'work_id', 'rating'], dtype=float)
            mean_rating_by_user_id = df_train.groupby('user_id')['rating'].mean()
            print(mean_rating_by_user_id.head())
            df_train['user_mean_rating'] = df_train['user_id'].map(mean_rating_by_user_id)
            df_train['corrected_rating'] = df_train['rating'] - df_train['user_mean_rating']
            df_test['corrected_rating']  = df_test['rating']  - df_train['user_mean_rating']
            df_train[['user_id', 'work_id', 'rating']].to_csv('/tmp/train.dat', header=False, index=False)
            df_test[['user_id', 'work_id', 'rating']].to_csv('/tmp/test.dat', header=False, index=False)
            # pd.DataFrame(np.column_stack((X_train, y_train))).to_csv('/tmp/train.dat', header=False, index=False)
            # pd.DataFrame(np.column_stack((X_test, y_test))).to_csv('/tmp/test.dat', header=False, index=False)

            for algo in self.algos:
                model = algo.make_instance()
                start = datetime.now()
                logger.info('[{0} {1}-folding] pass={2}/{1}'.format(model.get_shortname(), nb_split, pass_index))
                model.set_parameters(self.anonymized.nb_users, self.anonymized.nb_works)
                model.fit(X_train, y_train)
                y_pred = model.predict(self.anonymized.X[i_test])
                logger.debug('Predicted: %s' % y_pred[:5])
                logger.debug('Was: %s' % self.anonymized.y[i_test][:5])
                logger.debug('Elapsed: %s', datetime.now() - start)

                metrics_values = self.compute_metrics(model, y_pred, i_test)
                for metric, value in metrics_values.items():
                    metrics[metric][model.get_shortname()].append(value)
            if not full_cv:
                break

        logger.info('Final results')
        for metric_name, algos in metrics.items():
            logger.info('Evaluation of {}:'.format(metric_name.upper()))
            for algo_name in algos.keys():
                if full_cv and nb_split > 1:
                    logger.info(self.format_final_result(algo_name,
                                                         algos[algo_name]))
                else:
                    mean = np.mean(algos[algo_name])
                    logger.info('[{}]: {:f}'.format(algo_name, mean))




class Command(BaseCommand):
    args = ''
    help = 'Reproducible comparison of recommendation algorithms'

    def add_arguments(self, parser):
        parser.add_argument('dataset_name', type=str)
        parser.add_argument('--full', action='store_true', help='Make a full cross validation instead of a single run',
                            default=False)
        parser.add_argument('-em', '--eval-metric',
                            dest='eval_metrics',
                            type=str,
                            default=['rmse'],
                            action='append',
                            help='Add an evaluation metric for comparing models (available: {})'
                            .format(', '.join(RecommendationAlgorithm.available_evaluation_metrics())))
        parser.add_argument('-exp', '--experiment-filename',
                            dest='experiment_filename',
                            type=str,
                            help='Specify an experiment filename (JSON format)',
                            default=DEFAULT_CONFIG_FILENAME)
        parser.add_argument('-sp', '--nb-split',
                            dest='nb_split',
                            type=int,
                            default=5,
                            help='How many splits should be done on the dataset using a sklearn ShuffleSplit '
                                 '(default: 5-fold)')
        parser.add_argument('-fancy', '--fancy-formatting',
                            dest='fancy_formatting',
                            action='store_true',
                            default=False,
                            help='Fancy format the final results in the format (mean ± std) cut to 5 digits '
                                 'after rounding to 6 digits.')

    def handle(self, *args, **options):
        verbosity_level = options.get('verbosity')
        dataset_name = options.get('dataset_name')
        full_cv = options.get('full')
        eval_metrics = options.get('eval_metrics')
        experiment_filename = options.get('experiment_filename')
        nb_split = options.get('nb_split')
        fancy_formatting = options.get('fancy_formatting')

        # We allow DEBUG to be the minimal level.
        # Refer to Logging Levels for more information, but basically, levels are in multiple of 10.
        # DEBUG = 10. INFO = 20.
        # Verbosity level starts at 1 by default.
        # FIXME: this should be abstracted somewhere for reuse with other management commands.
        mangaki_logger = logging.getLogger('mangaki')
        mangaki_logger.setLevel(logging.INFO - min(verbosity_level - 1, 1) * 10)
        if verbosity_level >= 3:
            for handler in mangaki_logger.handlers:
                mangaki_logging.set_advanced_formatting(handler)

        if not full_cv:
            logger.debug('Compare will perform only one run.')
        else:
            logger.debug('Compare will perform a full cross validation of {}-fold.'.format(nb_split))

        experiment = Experiment(dataset_name, eval_metrics, experiment_filename, fancy_formatting)
        experiment.compare_models(nb_split, full_cv=full_cv)
