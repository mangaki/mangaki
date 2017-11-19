import numpy as np
from scipy.sparse import coo_matrix
from sklearn.metrics.pairwise import cosine_similarity


class MangakiKNN:
    def __init__(self, nb_users, nb_works, nb_neighbors=20):
        self.nb_neighbors = nb_neighbors
        self.nb_users = nb_users
        self.nb_works = nb_works

    def fit(self, X, y):
        user_ids = X[:, 0]
        work_ids = X[:, 1]
        self.ratings = coo_matrix((y, (user_ids, work_ids)),
                                  shape=(self.nb_users, self.nb_works))
        self.ratings_by_user = self.ratings.tocsr()
        self.ratings_by_work = self.ratings.tocsc()
        self.user_similarity = cosine_similarity(self.ratings_by_user)

    def predict(self, X):
        y = []
        for user_id, work_id in X:
            closest_raters = list(self.ratings_by_work[:, work_id].indices)
            closest_raters.sort(
                key=lambda rater_id: self.user_similarity[user_id, rater_id],
                reverse=True)
            neighbor_ids = closest_raters[:self.nb_neighbors]
            rating = self.ratings_by_work[neighbor_ids, work_id].mean()
            y.append(rating)
        return np.array(y)

