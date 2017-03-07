from django.conf import settings
from mangaki.utils.chrono import Chrono
from sklearn.decomposition import NMF
from scipy.sparse import lil_matrix
from collections import Counter
import numpy as np
import csv
import os

PIG_ID = 0#1407 # QCTX=1434  JJ=1407  SebNL=1124

explanation = {
    0: 'FATE, URBAN FANTASY',
    1: 'MANGA SHONEN',
    2: 'CYBERPUNK',
    3: 'HAREM, ROMANTIC COMEDY',
    4: 'MECHA',
    5: 'GHIBLI',
    6: 'KYOANI, BEAUTIFUL ANIMATION',
    7: 'ANOTHER WORLD, HORROR',
    8: 'SURVIVAL',
    9: 'TOWARDS THE SKY',
    10: 'SEINEN',
    11: '(bruit)',
    12: '(bruit)',
    13: 'BEAUX GOSSES',
    14: 'MANGA SHONEN',
    15: '(bruit)',
    16: 'REFRESHING SLICE-OF-LIFE',
    17: 'URASAWA',
    18: 'SHAFT + KARA NO KYOUKAI',
    19: 'CONAN',
    20: 'SHONEN MOVIES',
    21: 'SHONEN ATMOSPHERIQUES',
    22: 'CLAMP ET AL.',
    23: 'POPULAIRES',
    24: 'APPRENTISSAGE (basket, manga, magie)',
    25: 'HÉROÏNE FORTE',
    26: 'FUJOSHI',
    27: 'URBAN FANTASY',
    29: 'SHONEN 90s',
}


class MangakiNMF(object):
    M = None
    W = None
    H = None
    def __init__(self, NB_COMPONENTS=10):
        self.NB_COMPONENTS = NB_COMPONENTS
        self.chrono = Chrono(True)
        with open(os.path.join(settings.BASE_DIR, '../data/works-ml.csv')) as f:
            self.works = [x for _, x in csv.reader(f)]
        with open(os.path.join(settings.BASE_DIR, '../data/tags-ml.csv')) as f:
            self.tags = [x.split('|') for _, x in csv.reader(f)]

    def set_parameters(self, nb_users, nb_works):
        self.nb_users = nb_users
        self.nb_works = nb_works

    def make_matrix(self, X, y):
        matrix = lil_matrix((self.nb_users, self.nb_works))
        for (user, work), rating in zip(X, y):
            matrix[user, work] = rating
        return matrix

    def fit(self, X, y):
        print("Computing M: (%i × %i)" % (self.nb_users, self.nb_works))
        matrix = self.make_matrix(X, y)

        model = NMF(n_components=self.NB_COMPONENTS, random_state=42)
        self.W = model.fit_transform(matrix)
        self.H = model.components_
        print('Shapes', self.W.shape, self.H.shape)
        self.M = self.W.dot(self.H)

        self.chrono.save('factor matrix')
        self.display_components()

    def predict(self, X):
        return self.M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)]

    def dot_tags(self, i):
        c = Counter()
        for _, j in sorted([(self.H[i][j], j) for j in range(self.nb_works)], reverse=True):
            if self.H[i][j] < 1:  # Insignificant
                break
            for tag in self.tags[j]:
                c[tag] += self.H[i][j]
        return c

    def display_components(self):
        for i in range(self.NB_COMPONENTS):
            # if self.W[PIG_ID][i]:
            percentage = round(self.W[PIG_ID][i] * 100 / self.W[PIG_ID].sum(), 1)
            print('# Composante %d : %s (%.1f %%)' % (i, self.dot_tags(i).most_common(10), percentage))
            for _, title in sorted([(self.H[i][j], self.works[j]) for j in range(self.nb_works)], reverse=True)[:15]:
                print(title, _)
            print()

    def __str__(self):
        return '[NMF]'

    def get_shortname(self):
        return 'nmf'
