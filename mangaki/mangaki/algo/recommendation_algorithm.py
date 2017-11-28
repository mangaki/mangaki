import logging
from django.conf import settings
from mangaki.algo.side import SideInformation
from mangaki.utils.chrono import Chrono
from sklearn.metrics import mean_squared_error, mean_absolute_error
import pickle
import os.path


class RecommendationAlgorithmFactory:
    def __init__(self):
        self.algorithm_registry = {}
        self.algorithm_factory = {}
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.initialized = False
        self.size = 0

    def initialize(self):
        # FIXME: make it less complicated and go for a commonly used design pattern.
        # Behind the hood, it's called in `utils.__init__.py` which triggers the `algos.__init__.py`
        # which in turn triggers registration on this instance.
        # Then, once it reach `recommendation_algorithm` file, it's good to go.
        self.logger.debug('Recommendation algorithm factory initialized. {} algorithms available in the factory.'
                         .format(len(self.algorithm_registry)))
        self.initialized = True

    def register(self, name, klass, default_kwargs):
        self.algorithm_registry[name] = klass
        self.algorithm_factory[name] = default_kwargs
        self.logger.debug('Registered {} as a recommendation algorithm'.format(name))


class RecommendationAlgorithm:
    factory = RecommendationAlgorithmFactory()

    def __init__(self):
        self.verbose_level = settings.RECO_ALGORITHMS_VERBOSE_LEVEL
        self.chrono = Chrono(self.verbose_level)
        self.nb_users = None
        self.nb_works = None
        self.size = 0  # For backup files

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
        self.size = os.path.getsize(self.get_backup_path(filename)) / 1e6

    def load(self, filename):
        """
        This function raises FileNotFoundException if no backup exists.
        """
        with open(self.get_backup_path(filename), 'rb') as f:
            backup = pickle.load(f)
        return backup

    def load_tags(self, T=None, perform_scaling=True, with_mean=False):
        side = SideInformation(T, perform_scaling, with_mean)
        self.nb_tags = side.nb_tags
        self.T = side.T

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

    def compute_all_errors(self, X_train, y_train, X_test, y_test):
        y_train_pred = self.predict(X_train)
        logging.info('Train RMSE=%f', self.compute_rmse(y_train, y_train_pred))
        y_test_pred = self.predict(X_test)
        logging.info('Test RMSE=%f', self.compute_rmse(y_test, y_test_pred))

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
        default_kwargs = cls.factory.algorithm_factory.get(name) or {}
        if not klass:
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
