import logging

from mangaki.algo import RecommendationAlgorithm, register_algorithm
from django.conf import settings
from scipy.sparse import coo_matrix, load_npz, issparse
from sklearn.linear_model import Lasso
from sklearn.preprocessing import scale
from collections import Counter, defaultdict
from mangaki.utils.stats import avgstd
import os.path
import numpy as np


def relu(x):
    return max(-2, min(2, x))


def load_and_scale_tags(T=None, perform_scaling=True, with_mean=False):
    # Load in CSC format if no matrix provided.
    if T is None:
        T = load_npz(os.path.join(settings.DATA_DIR, 'lasso', 'tag-matrix.npz')).tocsc()

    nb_tags = T.shape[1]

    if perform_scaling:
        # Densify T to prevent sparsity destruction (which will anyway result in an exception).
        if with_mean and issparse(T):
            T = T.toarray()

        T = scale(T, with_mean=with_mean, copy=False)

        # If it's still sparse, let's get a dense version.
        if issparse(T):
            T = T.toarray()
    else:
        T = T.toarray() if issparse(T) else T

    return nb_tags, T


@register_algorithm('lasso')
class MangakiLASSO(RecommendationAlgorithm):
    def __init__(self, with_bias=True, alpha=0.01):
        super().__init__()
        self.alpha = alpha
        self.with_bias = with_bias
        self.logger = logging.getLogger(__name__ + '.' + self.get_shortname())

    def load_tags(self, T=None, perform_scaling=True, with_mean=False):
        self.nb_tags, self.T = load_and_scale_tags(T, perform_scaling, with_mean)

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
