from django.conf import settings
from mangaki.utils.chrono import Chrono
import pickle
import os.path


PICKLE_DIR = os.path.join(settings.BASE_DIR, '../pickles')


class RecommendationAlgorithm:
    nb_users = None
    nb_works = None
    chrono = None
    def __init__(self):
        self.chrono = Chrono(True)

    def save(self, filename):
        with open(os.path.join(PICKLE_DIR, filename), 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    def load(self, filename):
        with open(os.path.join(PICKLE_DIR, filename), 'rb') as f:
            backup = pickle.load(f)
        return backup

    def set_parameters(self, nb_users, nb_works):
        self.nb_users = nb_users
        self.nb_works = nb_works

    def get_shortname(self):
        return 'algo'

    def __str__(self):
        return '[%s]' % self.get_shortname().upper()
