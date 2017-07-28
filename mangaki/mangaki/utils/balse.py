from mangaki.utils.common import RecommendationAlgorithm
from mangaki.utils.algo import get_algo_backup, get_dataset_backup
from mangaki.utils.als import MangakiALS
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
        self.load_tags()
        self.als = MangakiALS(10)
        self.als.set_parameters(self.nb_users, self.nb_works)
        self.als.fit(X, y)
        y_pred = self.als.predict(X)
        row = X[:, 0]
        col = X[:, 1]
        data = y - y_pred
        print(type(y))
        print('dt', y.dtype)
        print(row[:5])
        M_res = coo_matrix((data, (row, col)), shape=(self.nb_users, self.nb_works))
        print(M_res)
        M_res = M_res.tocsr()
        self.reg = defaultdict(lambda: LinearRegression())
        user_ids = sorted(set(row))
        for user_id in user_ids:
            indices = M_res[user_id].indices
            values = M_res[user_id].data
            self.reg[user_id].fit(self.T[indices], values)
            if user_id % 100 == 0:
                print(user_id)

    def predict(self, X):
        # return self.M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)] + self.means[X[:, 0].astype(np.int64)]
        y_pred = self.als.predict(X)
        y_delta_res = []
        for user_id, work_id in X:
            if user_id not in self.reg:
                print(user_id, 'not')
                y_delta_res.append(0)
            else:
                y_delta_res.append(relu(self.reg[user_id].predict(self.T[work_id].reshape(1, -1))[0]))
        return y_pred + y_delta_res

    def get_shortname(self):
        return 'balse-%d' % self.NB_COMPONENTS
