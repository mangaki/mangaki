import importlib
import json
from typing import Type, List, Any, Dict, Optional

from django.core.management.base import BaseCommand

from collections import defaultdict
from sklearn.model_selection import ShuffleSplit
import numpy as np

from mangaki.utils.algos.recommendation_algorithm import RecommendationAlgorithm
from mangaki.utils.algos.dataset import Dataset
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

        Read the available algorithms from `algos` section.
        Register them under a short name provided or their static name (i.e. `class_name[len('Mangaki'):].lower()`).

        Read the configuration for the experiment as a (short_name, …params) tuple.
        Wrap configuration in an AlgorithmWrapper which will create instance during comparisons.

        Populate the `self.algos` list with wrappers.

        May raise ValueError or KeyError if the experiment file is malformed or invalid.
        Also, if the algorithms does not exists (import failure).

        Returns: None.

        """
        with open(self.experiment_filename, 'r') as f:
            experiment_data = json.loads(f.read())

        algos = experiment_data['algos']
        classes = {}
        for algo in algos:
            *mod_paths, class_name = algo['class'].split('.')
            mod_path = '.'.join(mod_paths)
            mod = importlib.import_module(mod_path)
            klass = getattr(mod, class_name)
            if not klass:
                raise ValueError('No class named `{}` in module `{}`'.format(class_name, mod_path))

            algo_name = algo.get('short_name', klass.static_name())
            classes[algo_name] = klass
            logger.debug('Registered {} as an available algorithm.'.format(algo_name))

        configurations = experiment_data['configurations']
        for config in configurations:
            short_name, *params = config
            klass = classes[short_name]
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
            if model.verbose:
                logger.debug('{} ({}) {:f}'.format(metric,
                                                   i_test,
                                                   results[metric]))

        return results

    def compare_models(self):
        k_fold = ShuffleSplit(n_splits=NB_SPLIT)
        metrics = defaultdict(lambda: defaultdict(list))

        pass_index = 0
        for i_train, i_test in k_fold.split(self.anonymized.X):
            for algo in self.algos:
                model = algo.make_instance()
                logger.info('[{0} {1}-folding] pass={2}/{1}'.format(model.get_shortname(), NB_SPLIT, pass_index + 1))
                model.set_parameters(self.anonymized.nb_users, self.anonymized.nb_works)
                model.fit(self.anonymized.X[i_train], self.anonymized.y[i_train])
                y_pred = model.predict(self.anonymized.X[i_test])
                if model.verbose:
                    logger.info('Predicted: %s' % y_pred[:5])
                    logger.info('Was: %s' % self.anonymized.y[i_test][:5])

                metrics_values = self.compute_metrics(model, y_pred, i_test)
                for metric, value in metrics_values.items():
                    metrics[metric][model.get_shortname()].append(value)

            pass_index += 1

        logger.info('Final results')
        for metric_name, algos in metrics.items():
            logger.info('Evaluation metric with {} results:'.format(metric_name))
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
    help = 'Compare recommendation algorithms'

    def add_arguments(self, parser):
        parser.add_argument('dataset_name', type=str)
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

    def handle(self, *args, **options):
        dataset_name = options.get('dataset_name')
        eval_metrics = options.get('eval_metrics', ['rmse'])
        experiment_filename = options.get('experiment_filename', None)

        experiment = Experiment(dataset_name, eval_metrics, experiment_filename)
        experiment.compare_models()
