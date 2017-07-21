from django.conf import settings
from mangaki.utils.chrono import Chrono
from sklearn.metrics import mean_squared_error, mean_absolute_error
import pickle
import os.path


class RecommendationAlgorithm:
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
    def static_name(cls):
        return cls.__name__[len('Mangaki'):].lower()

    def __str__(self):
        return '[%s]' % self.get_shortname().upper()
