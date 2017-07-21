from django.conf import settings

from mangaki.utils.algos.recommendation_algorithm import RecommendationAlgorithm
from sklearn.decomposition import NMF
from scipy.sparse import lil_matrix
import numpy as np
import csv
import os

PIG_ID = 1124#1407 # QCTX=1434  JJ=1407  SebNL=1124

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


class MangakiNMF(RecommendationAlgorithm):
    M = None
    W = None
    H = None
    def __init__(self, NB_COMPONENTS=10):
        super().__init__()
        self.NB_COMPONENTS = NB_COMPONENTS
        with open(os.path.join(settings.BASE_DIR, '../data/works.csv')) as f:
            self.works = [x for _, x in csv.reader(f)]

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
        # self.display_components()

    def predict(self, X):
        return self.M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)]

    def display_components(self):
        for i in range(self.NB_COMPONENTS):
            if self.W[PIG_ID][i]:
                percentage = round(self.W[PIG_ID][i] * 100 / self.W[PIG_ID].sum(), 1)
                print('# Composante %d : %s (%.1f %%)' % (i, explanation.get(i), percentage))
                """for _, title in sorted((-self.H[i][j], self.works[j]) for j in range(self.nb_works))[:10]:
                    print(title)
                print()"""

    def __str__(self):
        return '[NMF]'

    def get_shortname(self):
        return 'nmf'
