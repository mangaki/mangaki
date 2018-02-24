from mangaki.algo.recommendation_algorithm import RecommendationAlgorithm, register_algorithm
from scipy.sparse import coo_matrix
from collections import defaultdict
import numpy as np


@register_algorithm('als3', {'nb_components': 20})
class MangakiALS3(RecommendationAlgorithm):
    def __init__(self, nb_components=20, nb_iterations=20, lambda_=0.1):
        super().__init__()
        self.nb_components = nb_components
        self.nb_iterations = nb_iterations
        self.lambda_ = lambda_

    @property
    def is_serializable(self):
        return True

    def fit(self, X, y):
        # self.X_test = X_test
        # self.y_test = y_test
        self.init_vars()
        self.bias = y.mean()
        self.matrix, self.matrixT = self.to_dict(X, y)
        self.ratings_of_user, self.ratings_of_work = self.to_sparse(X, y)
        users, works = map(np.unique, self.ratings_of_user.nonzero())
        for nb_iter in range(self.nb_iterations):
            # print('Step', nb_iter, self.compute_rmse(self.y_test, self.predict(self.X_test)))
            for user_id in users:
                self.fit_user(user_id)
            for work_id in works:
                self.fit_work(work_id)

    def to_dict(self, X, y):
        matrix = defaultdict(dict)
        matrixT = defaultdict(dict)
        for (user_id, work_id), rating in zip(X, y):
            matrix[user_id][work_id] = rating
            matrixT[work_id][user_id] = rating
        return matrix, matrixT

    def to_sparse(self, X, y):
        user_ids, work_ids = zip(*X)  # Columns of X
        ratings = coo_matrix((y, (user_ids, work_ids)), shape=(self.nb_users, self.nb_works))
        return ratings.tocsr(), ratings.tocsc()

    def init_vars(self):
        self.U = np.random.multivariate_normal(mean=np.zeros(self.nb_components), cov=np.eye(self.nb_components), size=self.nb_users)
        self.V = np.random.multivariate_normal(mean=np.zeros(self.nb_components), cov=np.eye(self.nb_components), size=self.nb_works)
        self.W_user = np.random.normal(size=self.nb_users)
        self.W_work = np.random.normal(size=self.nb_works)
        self.bias = 0

    def fit_user(self, user_id):
        Ji = np.array(list(self.matrix[user_id].keys()))
        Ri = np.array(list(self.matrix[user_id].values()))
        Ni = Ji.size
        Vi = self.V[Ji]
        Wi = self.W_work[Ji]
        bi = self.W_user[user_id] + self.bias
        Li = self.lambda_ * Ni * np.eye(self.nb_components)
        self.U[user_id] = np.linalg.solve(Vi.T.dot(Vi) + Li, (Ri - Wi - bi).dot(Vi))
        self.W_user[user_id] = (Ri - self.U[user_id].dot(Vi.T) - Wi).mean() / (1 + self.lambda_) - self.bias

    def fit_work(self, work_id):
        Ij = np.array(list(self.matrixT[work_id].keys()))
        Rj = np.array(list(self.matrixT[work_id].values()))
        Nj = Ij.size
        Uj = self.U[Ij]
        Wj = self.W_user[Ij]
        bj = self.W_work[work_id] + self.bias
        Lj = self.lambda_ * Nj * np.eye(self.nb_components)
        self.V[work_id] = np.linalg.solve(Uj.T.dot(Uj) + Lj, (Rj - Wj - bj).dot(Uj))
        self.W_work[work_id] = (Rj - self.V[work_id].dot(Uj.T) - Wj).mean() / (1 + self.lambda_) - self.bias

    def predict(self, X):
        user_ids, work_ids = zip(*X)
        self.M = self.U.dot(self.V.T) + self.W_user.reshape(-1, 1) + self.W_work.reshape(1, -1) + self.bias
        return self.M[user_ids, work_ids]

    def get_shortname(self):
        return 'als3-%d' % self.nb_components
