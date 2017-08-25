from mangaki.utils.common import RecommendationAlgorithm
from mangaki.settings import DATA_DIR
from scipy.sparse import coo_matrix, load_npz
from sklearn.linear_model import Lasso
from sklearn.preprocessing import scale
from collections import Counter, defaultdict
from mangaki.utils.stats import avgstd
import os.path


def relu(x):
    return max(-2, min(2, x))


class MangakiLASSO(RecommendationAlgorithm):
    def __init__(self, with_bias=True, alpha=0.01):
        super().__init__()
        self.alpha = alpha
        self.with_bias = with_bias

    def load_tags(self, T=None):
        if T is None:
            T = load_npz(os.path.join(DATA_DIR, 'balse/tag-matrix.npz')).tocsc()
            T_scaled = scale(T, with_mean=False).toarray()
        _, self.nb_tags = T.shape
        self.T = T_scaled

    def fit(self, X, y):
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
            if user_id % 500 == 0:
                print(user_id)
        self.compute_sparsity()

    def predict(self, X):
        y_pred = []
        for user_id, work_id in X:
            if user_id not in self.reg:
                print(user_id, 'not')
                y_pred.append(0)
            else:
                y_pred.append(relu(self.reg[user_id].predict(self.T[work_id].reshape(1, -1))[0]))
        return y_pred

    def compute_sparsity(self):
        sparsity = []
        for user_id in self.reg:
            nb_features = sum(weight != 0 for weight in self.reg[user_id].coef_)
            sparsity.append(nb_features)
        print('Sparsity', avgstd(sparsity))

    def get_shortname(self):
        return 'lasso-%d' % self.NB_COMPONENTS
