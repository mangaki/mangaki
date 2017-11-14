from collections import Counter, defaultdict

import numpy as np
from scipy.sparse import coo_matrix
from sklearn.metrics.pairwise import cosine_similarity

from mangaki.algo.recommendation_algorithm import RecommendationAlgorithm, register_algorithm


@register_algorithm('knn2')
class MangakiKNN2(RecommendationAlgorithm):
    '''
    Toy implementation (not usable in production) of KNN for the mere sake of science.
    N users, M ~ 10k works, P ~ 300k user-work pairs, K neighbors.

    Algorithm:
    For each user-work pair (over all P pairs):
    - Find closest raters of user *who rated this work* (takes O(M log M))
    - Compute their average rating (takes O(K))
    Complexity: O(P·(M log M + K)) => Oops!
    '''
    nb_neighbors = None
    closest_neighbors = None
    rated_works = None
    mean_score = None
    ratings = None
    sum_ratings = None
    nb_ratings = None
    M = None
    def __init__(self, nb_neighbors=20):
        super().__init__()
        self.nb_neighbors = nb_neighbors
        self.ratings = None

    def load(self, filename):
        backup = super().load(filename)
        self.nb_neighbors = backup.nb_neighbors
        self.closest_neighbors = backup.closest_neighbors
        self.rated_works = backup.rated_works
        self.mean_score = backup.mean_score
        self.ratings = backup.ratings
        self.sum_ratings = backup.sum_ratings
        self.nb_ratings = backup.nb_ratings
        self.M = backup.M
        self.nb_works = backup.nb_works
        self.nb_users = backup.nb_users

    @property
    def is_serializable(self):
        return True

    def fit(self, X, y, whole_dataset=False):
        user_ids = X[:, 0]
        work_ids = X[:, 1]
        self.ratings = coo_matrix((y, (user_ids, work_ids)), shape=(self.nb_users, self.nb_works)).astype(np.float64)
        self.ratings_by_user = self.ratings.tocsr()
        self.ratings_by_work = self.ratings.tocsc()
        self.user_similarity = cosine_similarity(self.ratings_by_user)

    def predict(self, X):
        y = []
        for user_id, work_id in X:
            users_who_rated_it = list(self.ratings_by_work[:, work_id].indices)
            users_who_rated_it.sort(key=lambda neighbor_id: self.user_similarity[user_id, neighbor_id], reverse=True)
            neighbor_ids = users_who_rated_it[:self.nb_neighbors]
            rating = self.ratings_by_work[users_who_rated_it, work_id].mean()
            y.append(rating)
        return np.array(y)

    def __str__(self):
        return '[KNN2] NB_NEIGHBORS = %d' % self.nb_neighbors

    def get_shortname(self):
        return 'knn2-%d' % self.nb_neighbors
