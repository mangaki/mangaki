import json
import importlib
from typing import Type, List, Any, Dict, Optional

from django.core.management.base import BaseCommand

from collections import defaultdict
from sklearn.model_selection import ShuffleSplit
import numpy as np

from mangaki.utils.algos.recommendation_algorithm import RecommendationAlgorithm
from mangaki.utils.algos.dataset import Dataset
from mangaki.utils.values import rating_values
from mangaki.settings import DATA_DIR
import logging
import os.path

FILENAMES = {
    'movies': 'ratings-ml.csv',
    'mangas': 'ratings.csv'
}
CONVERT_FUNCTIONS = {
    'movies': float,
    'mangas': lambda choice: rating_values[choice]
}
DEFAULT_CONFIG_FILENAME = os.path.join(DATA_DIR, 'experiment_config.json')

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
    def __init__(self, dataset_name, eval_metrics, experiment_filename=None):
        self.algos = []

        self.experiment_filename = experiment_filename
        if experiment_filename:
            self.prepare_experiment()

        self.evaluation_metrics = eval_metrics
        self.anonymized = None
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
            if model.verbose_level:
                logger.debug('{} ({}) {:f}'.format(metric,
                                                   i_test,
                                                   results[metric]))

        return results

    def compare_models(self, nb_split: int = 5, full_cv: bool = False):
        k_fold = ShuffleSplit(n_splits=nb_split)
        metrics = defaultdict(lambda: defaultdict(list))

        for pass_index, (i_train, i_test) in enumerate(k_fold.split(self.anonymized.X), start=1):
            for algo in self.algos:
                model = algo.make_instance()
                logger.info('[{0} {1}-folding] pass={2}/{1}'.format(model.get_shortname(), nb_split, pass_index))
                model.set_parameters(self.anonymized.nb_users, self.anonymized.nb_works)
                model.fit(self.anonymized.X[i_train], self.anonymized.y[i_train])
                y_pred = model.predict(self.anonymized.X[i_test])
                if model.verbose_level >= 2:
                    logger.info('Predicted: %s' % y_pred[:5])
                    logger.info('Was: %s' % self.anonymized.y[i_test][:5])

                metrics_values = self.compute_metrics(model, y_pred, i_test)
                for metric, value in metrics_values.items():
                    metrics[metric][model.get_shortname()].append(value)
            if not full_cv:
                break

        logger.info('Final results')
        for metric_name, algos in metrics.items():
            logger.info('Evaluation of {}:'.format(metric_name.upper()))
            for algo_name in algos.keys():
                mean = np.mean(algos[algo_name])
                var = np.var(algos[algo_name])
                std = var ** 0.5
                logger.info('[{}]: mean={:f} var={:f} std={:f}'.format(
                    algo_name,
                    mean,
                    var,
                    std
                ))


class Command(BaseCommand):
    args = ''
    help = 'Reproducible comparison of recommendation algorithms'

    def add_arguments(self, parser):
        parser.add_argument('dataset_name', type=str)
        parser.add_argument('--full', action='store_true', help='Make a full cross validation instead of a single run')
        parser.add_argument('-em', '--eval-metric',
                            dest='eval_metrics',
                            type=str,
                            action='append',
                            help='Add an evaluation metric for comparing models (available: {})'
                            .format(', '.join(RecommendationAlgorithm.available_evaluation_metrics())))
        parser.add_argument('-exp', '--experiment-filename',
                            dest='experiment_filename',
                            type=str,
                            help='Specify an experiment filename (JSON format)')
        parser.add_argument('-sp', '--nb-split',
                            dest='nb_split',
                            type=int,
                            default=5,
                            help='How many splits should be done on the dataset using a sklearn ShuffleSplit '
                                 '(default: 5-fold)')

    def handle(self, *args, **options):
        dataset_name = options.get('dataset_name')
        full_cv = options.get('full')
        eval_metrics = options.get('eval_metrics') or ['rmse']
        experiment_filename = options.get('experiment_filename') or DEFAULT_CONFIG_FILENAME

        experiment = Experiment(dataset_name, eval_metrics, experiment_filename)
        experiment.compare_models(options.get('nb_split'), full_cv=full_cv)
