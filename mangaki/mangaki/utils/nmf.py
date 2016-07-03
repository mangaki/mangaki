from mangaki.utils.chrono import Chrono
from sklearn.decomposition import NMF
from scipy.sparse import lil_matrix
import numpy as np
import pandas


class MangakiNMF(object):
    M = None
    W = None
    H = None
    def __init__(self, NB_COMPONENTS=10):
        self.NB_COMPONENTS = NB_COMPONENTS
        self.chrono = Chrono(True)
        self.works = pandas.read_csv('data/works.csv', header=None).as_matrix()[:, 1]

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

    def display_components(self):
        for i in range(self.NB_COMPONENTS):
            print('# Component %d:' % i, )
            for _, title in sorted((-self.H[i][j], self.works[j]) for j in range(self.nb_works))[:10]:
                print(title)
            print()

    def __str__(self):
        return '[NMF]'

    def get_shortname(self):
        return 'nmf'
