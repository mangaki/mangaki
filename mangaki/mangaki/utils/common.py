from django.conf import settings
from mangaki.utils.chrono import Chrono
import pickle
import os.path


PICKLE_DIR = os.path.join(settings.BASE_DIR, '../pickles')


class RecommendationAlgorithm:
    def __init__(self):
        self.chrono = Chrono(True)
        self.nb_users = None
        self.nb_works = None

    def get_backup_path(self, filename):
        return os.path.join(PICKLE_DIR, self.get_backup_filename())

    def has_backup(self, filename=None):
        if filename is None:
            filename = self.get_backup_filename()
        return os.path.isfile(self.get_backup_path(filename))

    def save(self, filename):
        with open(self.get_backup_path(filename), 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    def load(self, filename):
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

    def __str__(self):
        return '[%s]' % self.get_shortname().upper()
