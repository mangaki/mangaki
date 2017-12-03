import logging

from mangaki.algo import RecommendationAlgorithm, register_algorithm
from scipy.sparse import coo_matrix
from sklearn.linear_model import Lasso
from collections import Counter, defaultdict
from mangaki.utils.stats import avgstd
import os.path
import numpy as np


def relu(x):
    return max(-2, min(2, x))


@register_algorithm('lasso')
class MangakiLASSO(RecommendationAlgorithm):
    def __init__(self, with_bias=True, alpha=0.01, T=None):
        super().__init__()
        self.alpha = alpha
        self.with_bias = with_bias
        self.logger = logging.getLogger(__name__ + '.' + self.get_shortname())
        self.T = T

    def fit(self, X, y, autoload_tags=True):
        if self.T is None and autoload_tags:
            self.load_tags()

        row = X[:, 0]
        col = X[:, 1]
        self.nb_rated = Counter(col)
        data = y
        M = coo_matrix((data, (row, col)), shape=(self.nb_users, self.nb_works)).tocsr()
        self.reg = defaultdict(lambda: Lasso(alpha=self.alpha, fit_intercept=self.with_bias))
        user_ids = sorted(set(row))
        for user_id in user_ids:
            indices = M[user_id].indices
            values = M[user_id].data
            self.reg[user_id].fit(self.T[indices], values)
            # TODO: cuter progress information with tqdm.
            if user_id % 500 == 0:
                self.logger.debug('Fitting user ID {:d}/{:d}…'.format(user_id, len(user_ids)))

        # Black magic of high level, freeze the defaultdict (i.e. remove the default factory).
        self.reg.default_factory = None
        self.user_sparsities = self.compute_user_sparsities()
        self.logger.info('Sparsity: {}'.format(avgstd(self.user_sparsities)))

    def predict(self, X):
        y_pred = np.zeros(X.shape[0])
        for index, (user_id, work_id) in enumerate(X):
            if user_id in self.reg:
                y_pred[index] = (relu(
                    # Get the *unique* and first element of the prediction array.
                    self.reg[user_id].predict(
                        # We need to get a N × 1 array for the regressor.
                        self.T[work_id].reshape(1, -1)
                    )
                    [0]
                ))

        return y_pred

    def compute_user_sparsities(self):
        return [np.count_nonzero(reg.coef_) for reg in self.reg.values()]

    def get_shortname(self):
        return 'lasso{}{:f}'.format('-with_bias-' if self.with_bias else '-', self.alpha)
