from mangaki.utils.common import RecommendationAlgorithm
from mangaki.utils.algo import get_algo_backup, get_dataset_backup
from mangaki.utils.als import MangakiALS
from mangaki.utils.lasso import MangakiLASSO
from scipy.sparse import coo_matrix, load_npz
from sklearn.linear_model import LinearRegression
from collections import defaultdict
import numpy as np


def relu(x):
    return max(-2, min(2, x))


class MangakiBALSE(RecommendationAlgorithm):
    M = None
    U = None
    VT = None
    def __init__(self, NB_COMPONENTS=10, NB_ITERATIONS=10, LAMBDA=0.1):
        super().__init__()
        self.NB_COMPONENTS = NB_COMPONENTS
        self.NB_ITERATIONS = NB_ITERATIONS
        self.LAMBDA = LAMBDA

    def load_tags(self, T=None):
        # From file
        if T is None:
            T = load_npz('data/balse/tag-matrix.npz').toarray()
        _, self.nb_tags = T.shape
        self.T = T

    def fit(self, X, y):
        #self.load_tags()
        self.als = MangakiALS(10)
        self.als.set_parameters(self.nb_users, self.nb_works)
        self.als.fit(X, y)
        #y_pred = self.als.predict(X)
        self.lasso = MangakiLASSO()
        self.lasso.set_parameters(self.nb_users, self.nb_works)
        self.lasso.fit(X, y)

    def predict(self, X):
        # return self.M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)] + self.means[X[:, 0].astype(np.int64)]
        y_als = self.als.predict(X)
        y_lasso = self.lasso.predict(X)
        y_pred = []
        for i, (user_id, work_id) in enumerate(X):
            if self.lasso.nb_rated[work_id] < 5:
                y_pred.append(y_lasso[i])
            else:
                y_pred.append(y_als[i])
        return y_pred

    def get_shortname(self):
        return 'balse-%d' % self.NB_COMPONENTS
