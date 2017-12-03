from mangaki.utils.common import RecommendationAlgorithm
from django.conf import settings
from mangaki.utils.chrono import Chrono
from sklearn.decomposition import FactorAnalysis
from scipy.sparse import csr_matrix
import numpy as np


class MangakiEFA(RecommendationAlgorithm):
    '''Factor Analysis:
    See http://scikit-learn.org/stable/modules/decomposition.html#factor-analysis
    Better way to get interpretable components, see MangakiNMF'''
    M = None
    W = None
    H = None
    def __init__(self, NB_COMPONENTS=20):
        self.NB_COMPONENTS = NB_COMPONENTS
        self.chrono = Chrono(True)

    def set_parameters(self, nb_users, nb_works):
        self.nb_users = nb_users
        self.nb_works = nb_works

    def make_matrix(self, X, y):
        rows = X[:, 0].astype(np.int64)
        cols = X[:, 1].astype(np.int64)
        data = y.astype(np.int64)
        return csr_matrix((data, (rows, cols)), shape=(self.nb_users, self.nb_works))

    def fit(self, X, y, truncated=None):
        print("Computing M: (%i × %i)" % (self.nb_users, self.nb_works))
        matrix = self.make_matrix(X, y)

        model = FactorAnalysis(n_components=self.NB_COMPONENTS)
        matrix = matrix.toarray()
        self.matrix = matrix
        if truncated is not None:
            matrix = matrix[:, :truncated]
        self.W = model.fit_transform(matrix)
        self.H = model.components_
        print('Shapes', self.W.shape, self.H.shape)
        self.M = self.W.dot(self.H) + model.mean_
        self.model = model

        self.chrono.save('factor matrix')

    def fit_user(self, user_id, sparse_matrix_dict):
        pass

    def predict(self, X):
        return self.M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)]

    def __str__(self):
        return '[EFA]'

    def get_shortname(self):
        return 'efa'
