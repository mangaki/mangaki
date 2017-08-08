from mangaki.utils.common import RecommendationAlgorithm
#from mangaki.utils.algo import get_algo_backup, get_dataset_backup
#from mangaki.utils.als import MangakiALS
from scipy.sparse import coo_matrix, load_npz
from sklearn.linear_model import LinearRegression, Lasso
from collections import Counter, defaultdict
import numpy as np


def relu(x):
    return max(-2, min(2, x))


class MangakiLASSO(RecommendationAlgorithm):
    def __init__(self, NB_COMPONENTS=10, NB_ITERATIONS=10, LAMBDA=0.1):
        super().__init__()
        self.NB_COMPONENTS = NB_COMPONENTS
        self.NB_ITERATIONS = NB_ITERATIONS
        self.LAMBDA = LAMBDA

    def load_tags(self, T=None):
        # From file
        if T is None:
            T = load_npz('../data/balse/tag-matrix.npz').toarray()
        _, self.nb_tags = T.shape
        self.T = T

    def fit(self, X, y):
        self.load_tags()
        row = X[:, 0]
        col = X[:, 1]
        self.nb_rated = Counter(col)
        data = y
        M = coo_matrix((data, (row, col)), shape=(self.nb_users, self.nb_works)).tocsr()
        self.reg = defaultdict(lambda: Lasso(alpha=0.001, normalize=True))
        user_ids = sorted(set(row))
        for user_id in user_ids:
            indices = M[user_id].indices
            values = M[user_id].data
            self.reg[user_id].fit(self.T[indices], values)
            if user_id % 100 == 0:
                print(user_id)

    def predict(self, X):
        y_pred = []
        for user_id, work_id in X:
            if user_id not in self.reg:
                print(user_id, 'not')
                y_pred.append(0)
            else:
                y_pred.append(relu(self.reg[user_id].predict(self.T[work_id].reshape(1, -1))[0]))
        return y_pred

    def get_shortname(self):
        return 'balse-%d' % self.NB_COMPONENTS
