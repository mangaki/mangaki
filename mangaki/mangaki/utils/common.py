import importlib

import logging
from django.conf import settings
from mangaki.utils.chrono import Chrono
from sklearn.metrics import mean_squared_error, mean_absolute_error
import pickle
import os.path

# FIXME: You should really disregard this.
# Rationale: until we can move all algorithms into a `algos/` subfolder, we cannot recognize an algorithm except
# if we import every files here. Which we don't want to do. So let's hardcode.
_REMOVE_ME_SOON_OR_FIRE_RAITO = [
    'mangaki.utils.als',
    'mangaki.utils.svd',
    'mangaki.utils.knn',
    'mangaki.utils.zero'
]
class RecommendationAlgorithmFactory:
    def __init__(self):
        self.algorithm_registry = {}
        self.algorithm_factory = {}
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.initialized = False

    def initialize(self):
        for name in _REMOVE_ME_SOON_OR_FIRE_RAITO:
            importlib.import_module(name)

        self.logger.info('Recommendation algorithm factory initialized. {} algorithms available in the factory.'
                         .format(len(self.algorithm_registry)))
        self.initialized = True

    def register(self, name, klass, default_kwargs):
        self.algorithm_registry[name] = klass
        self.algorithm_factory[name] = default_kwargs
        self.logger.info('Registered {} as a recommendation algorithm'.format(name))

class RecommendationAlgorithm:
    factory = RecommendationAlgorithmFactory()

    def __init__(self):
        self.verbose = settings.RECO_ALGORITHMS_DEFAULT_VERBOSE
        self.chrono = Chrono(self.verbose)
        self.nb_users = None
        self.nb_works = None

    def get_backup_path(self, filename):
        if filename is None:
            filename = self.get_backup_filename()
        return os.path.join(settings.PICKLE_DIR, filename)

    def has_backup(self, filename=None):
        if filename is None:
            filename = self.get_backup_filename()
        return os.path.isfile(self.get_backup_path(filename))

    @property
    def is_serializable(self):
        return False

    def save(self, filename):
        with open(self.get_backup_path(filename), 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    def load(self, filename):
        """
        This function raises FileNotFoundException if no backup exists.
        """
        with open(self.get_backup_path(filename), 'rb') as f:
            backup = pickle.load(f)
        return backup

    def set_parameters(self, nb_users, nb_works):
        self.nb_users = nb_users
        self.nb_works = nb_works

    def get_shortname(self):
        return 'algo'

    def get_backup_filename(self):
        return '%s.pickle' % self.get_shortname()

    @staticmethod
    def compute_rmse(y_pred, y_true):
        return mean_squared_error(y_true, y_pred) ** 0.5

    @staticmethod
    def compute_mae(y_pred, y_true):
        return mean_absolute_error(y_true, y_pred)

    @staticmethod
    def available_evaluation_metrics():
        return ['rmse', 'mae']

    @classmethod
    def register_algorithm(cls, name, klass, default_kwargs=None):
        cls.factory.register(name, klass, default_kwargs)

    @classmethod
    def list_available_algorithms(cls):
        return list(cls.factory.algorithm_registry.keys())

    @classmethod
    def instantiate_algorithm(cls, name):
        klass = cls.factory.algorithm_registry.get(name)
        default_kwargs = cls.factory.algorithm_factory.get(name)
        if not klass or not default_kwargs:
            raise KeyError('No algorithm named "{}" in the registry! Did you forget a @register_algorithm? A typo?'
                           .format(name))

        return klass(**default_kwargs)

    def __str__(self):
        return '[%s]' % self.get_shortname().upper()


def register_algorithm(algorithm_name, default_kwargs=None):
    if default_kwargs is None:
        default_kwargs = {}

    def decorator(cls):
        RecommendationAlgorithm.register_algorithm(algorithm_name, cls, default_kwargs)
        return cls
    return decorator
