from mangaki.utils.common import RecommendationAlgorithm
from collections import Counter, defaultdict
import numpy as np
from scipy.sparse import coo_matrix
from sklearn.metrics.pairwise import cosine_similarity


class MangakiKNN(RecommendationAlgorithm):
    NB_NEIGHBORS = None
    closest_neighbors = None
    rated_works = None
    mean_score = None
    ratings = None
    sum_ratings = None
    nb_ratings = None
    M = None
    def __init__(self, NB_NEIGHBORS=20, RATED_BY_NEIGHBORS_AT_LEAST=3, missing_is_mean=True, weighted_neighbors=False):
        super().__init__()
        self.NB_NEIGHBORS = NB_NEIGHBORS
        self.RATED_BY_NEIGHBORS_AT_LEAST = RATED_BY_NEIGHBORS_AT_LEAST
        self.missing_is_mean = missing_is_mean
        self.weighted_neighbors = weighted_neighbors
        self.closest_neighbors = {}
        self.rated_works = {}
        self.mean_score = {}
        self.ratings = {}
        self.sum_ratings = {}
        self.nb_ratings = {}

    def get_neighbors(self, user_ids=None):
        neighbors = []
        if user_ids is None:
            score = cosine_similarity(self.M)  # All pairwise similarities
            user_ids = range(self.nb_users)
        else:
            score = cosine_similarity(self.M[user_ids], self.M)
        for i, user_id in enumerate(user_ids):
            if self.NB_NEIGHBORS < self.nb_users - 1:
                score[i][user_id] = float('-inf')  # Do not select the user itself while looking at its potential neighbors
                # Put top NB_NEIGHBORS user indices at the end of array, no matter their order; then, slice them!
                neighbor_ids = (
                    score[i]
                    .argpartition(-self.NB_NEIGHBORS - 1)
                    [-self.NB_NEIGHBORS - 1:-1]
                )
            else:
                neighbor_ids = list(range(len(score[i])))
                neighbor_ids.remove(user_id)
            neighbors.append(neighbor_ids)
            self.closest_neighbors[user_id] = {}
            for neighbor_id in neighbor_ids:
                self.closest_neighbors[user_id][neighbor_id] = score[i, neighbor_id]
        return neighbors

    def fit(self, X, y, whole_dataset=False):
        self.ratings = defaultdict(dict)
        self.sum_ratings = Counter()
        self.nb_ratings = Counter()
        users, works = zip(*list(X))
        self.M = coo_matrix((y,(users,works)), shape = (self.nb_users, self.nb_works)) # Might take some time, but coo is efficient for creating matrices
        self.M = M.toscr() # knn.M should be CSR for faster arithmetic operations
        for (user_id, work_id), rating in zip(X, y):
            self.ratings[user_id][work_id] = rating
            self.nb_ratings[work_id] += 1
            self.sum_ratings[work_id] += rating
        for work_id in self.nb_ratings:
            self.mean_score[work_id] = self.sum_ratings[work_id] / self.nb_ratings[work_id]

    def predict(self, X):
        self.get_neighbors(list(set(X[:, 0])))  # Compute only relevant neighbors
        y = []
        for my_user_id, work_id in X:
            weight = 0
            predicted_rating = 0
            nb_neighbors_that_rated_it = 0
            for user_id in self.closest_neighbors[my_user_id]:
                their_sim_score = self.closest_neighbors[my_user_id][user_id]
                if self.missing_is_mean:
                    if work_id in self.ratings[user_id]:
                        their_rating = self.ratings[user_id][work_id]
                        nb_neighbors_that_rated_it += 1
                    else:
                        their_rating = self.mean_score.get(work_id, 0)  # In case KNN was not trained on this work
                else:
                    their_rating = self.ratings[user_id].get(work_id)
                    if their_rating is None:
                        continue  # Skip
                if self.weighted_neighbors:
                    predicted_rating += their_sim_score * their_rating
                    weight += their_sim_score
                else:
                    predicted_rating += their_rating
                    weight += 1
            if nb_neighbors_that_rated_it < self.RATED_BY_NEIGHBORS_AT_LEAST:
                predicted_rating = 0
            if weight > 0:
                predicted_rating /= weight
            y.append(predicted_rating)
        return np.array(y)

    def __str__(self):
        return '[KNN] NB_NEIGHBORS = %d' % self.NB_NEIGHBORS

    def get_shortname(self):
        return 'knn-%d' % self.NB_NEIGHBORS
