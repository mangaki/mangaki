from mangaki.utils.common import RecommendationAlgorithm
from django.contrib.auth.models import User
from mangaki.models import Work
from collections import Counter, defaultdict
import numpy as np
from scipy.sparse import lil_matrix
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

    def __init__(self, NB_NEIGHBORS=20, RATED_BY_AT_LEAST=3, missing_is_mean=True, weighted_neighbors=False):
        super().__init__()
        self.NB_NEIGHBORS = NB_NEIGHBORS
        self.RATED_BY_AT_LEAST = RATED_BY_AT_LEAST
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
            if self.NB_NEIGHBORS < self.nb_users:
                neighbor_ids = score[i].argpartition(-self.NB_NEIGHBORS - 1)[
                               -self.NB_NEIGHBORS - 1:-1]  # Put top NB_NEIGHBORS user indices at the end of array, no matter their order; then, slice them!
            else:
                neighbor_ids = range(len(score[i]))
            neighbors.append(neighbor_ids)
            self.closest_neighbors[user_id] = {}
            for neighbor_id in neighbor_ids:
                self.closest_neighbors[user_id][neighbor_id] = score[i, neighbor_id]
        return neighbors

    def get_common_traits(self, my_username, username):
        my_user_id = User.objects.get(username=my_username).id
        user_id = User.objects.get(username=username).id
        self.rated_works = set(self.ratings[my_user_id].keys())
        agree = []
        disagree = []
        for work_id in self.rated_works & set(self.ratings[user_id].keys()):
            score = self.ratings[my_user_id][work_id] * self.ratings[user_id][work_id]
            if self.ratings[my_user_id][work_id] * self.ratings[user_id][work_id] > 0:
                agree.append((score, work_id, self.ratings[my_user_id][work_id], self.ratings[user_id][work_id]))
            elif self.ratings[my_user_id][work_id] * self.ratings[user_id][work_id] < 0:
                disagree.append((score, work_id, self.ratings[my_user_id][work_id], self.ratings[user_id][work_id]))
        agree.sort(reverse=True)
        disagree.sort()
        works = Work.objects.in_bulk(map(lambda x: x[1], agree + disagree))
        print('Strongly agree: (over %d positive products)' % len(agree))
        for rank, (_, work_id, my, their) in enumerate(agree, start=1):
            if abs(my) >= 1 and abs(their) >= 1:
                print('%d.' % rank, works[work_id].title, my, their, '=', my * their)
        print('Strongly disagree: (over %d negative products)' % len(disagree))
        for rank, (_, work_id, my, their) in enumerate(disagree, start=1):
            if abs(my) >= 1 and abs(their) >= 1:
                print('%d.' % rank, works[work_id].title, my, their, '=', my * their)

    def fit(self, X, y, whole_dataset=False):
        self.ratings = defaultdict(dict)
        self.sum_ratings = defaultdict(lambda: 0)
        self.nb_ratings = defaultdict(lambda: 0)
        self.M = lil_matrix((self.nb_users, self.nb_works))
        for (user_id, work_id), rating in zip(X, y):
            self.ratings[user_id][work_id] = rating
            self.nb_ratings[work_id] += 1
            self.sum_ratings[work_id] += rating
            self.M[user_id, work_id] = rating
        for work_id in self.nb_ratings:
            self.mean_score[work_id] = self.sum_ratings[work_id] / self.nb_ratings[work_id]

    def predict(self, X):
        self.get_neighbors(list(set(X[:, 0])))  # Compute only relevant neighbors
        y = []
        for my_user_id, work_id in X:
            weight = 0
            predicted_rating = 0
            for user_id in self.closest_neighbors[my_user_id]:
                their_sim_score = self.closest_neighbors[my_user_id][user_id]
                if self.missing_is_mean:
                    their_rating = self.ratings[user_id].get(work_id, self.mean_score.get(work_id,
                                                                                          0))  # Double fallback, in case KNN was not trained on this work
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
            if not self.weighted_neighbors and weight < self.RATED_BY_AT_LEAST:
                predicted_rating = 0
            if weight > 0:
                predicted_rating /= weight
            y.append(predicted_rating)
        return np.array(y)

    def __str__(self):
        return '[KNN] NB_NEIGHBORS = %d' % self.NB_NEIGHBORS

    def get_shortname(self):
        return 'knn-%d' % self.NB_NEIGHBORS
