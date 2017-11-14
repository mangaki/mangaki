import numpy as np
from scipy.sparse import coo_matrix
from sklearn.linear_model import Lasso


class MangakiLASSO:
    def __init__(self, nb_users, nb_works, T):
        self.nb_users = nb_users
        self.nb_works = nb_works
        self.T = T

    def fit(self, X, y):
        user_ids = X[:, 0]
        work_ids = X[:, 1]
        self.ratings = coo_matrix((y, (user_ids, work_ids)),
                                  shape=(self.nb_users, self.nb_works))
        self.ratings_by_user = self.ratings.tocsr()
        self.lasso = {}
        for user_id in range(self.nb_users):
            rated_work_ids = self.ratings_by_user[user_id].indices
            user_ratings = self.ratings_by_user[user_id].data
            if len(rated_work_ids):
                self.lasso[user_id] = Lasso(alpha=0.01, fit_intercept=True)
                self.lasso[user_id].fit(self.T[rated_work_ids], user_ratings)

    def predict(self, X):
        y = []
        for user_id, work_id in X:
            if user_id in self.lasso:
                y.append(self.lasso[user_id]
                             .predict(self.T[work_id].reshape(1, -1)))
        return np.array(y)
