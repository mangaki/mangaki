from django.contrib.auth.models import User
from mangaki.utils.values import rating_values
from collections import Counter
import numpy as np


class MangakiKNN(object):
    NB_NEIGHBORS = None
    closest_neighbors = {}
    rated_works = {}
    mean_score = {}
    ratings = {}
    sum_ratings = {}
    nb_ratings = {}
    def __init__(self, NB_NEIGHBORS=15):
        self.NB_NEIGHBORS = NB_NEIGHBORS
        self.closest_neighbors = {}
        self.rated_works = {}
        self.mean_score = {}
        self.ratings = {}
        self.sum_ratings = {}
        self.nb_ratings = {}

    def get_rated_works(self):
        self.rated_works = {}
        for work_id, choice in Rating.objects.filter(user__username=self.username).values_list('work_id', 'choice'):
            self.rated_works[work_id] = choice

    def get_neighbors(self, my_user_id):
        neighbors = Counter()
        rated_works = set(self.ratings[my_user_id].keys())
        for user_id in self.ratings:
            if user_id != my_user_id:
                for work_id in rated_works & set(self.ratings[user_id].keys()):
                    neighbors[user_id] += self.ratings[my_user_id][work_id] * self.ratings[user_id][work_id]

        self.closest_neighbors[my_user_id] = {}
        users = []
        for user_id, sim_score in neighbors.most_common(self.NB_NEIGHBORS):
            self.closest_neighbors[my_user_id][user_id] = sim_score
            users.append(User.objects.get(id=user_id).username)
        # print(users)

    def fit(self, X, y):
        self.ratings = {}
        self.sum_ratings = {}
        self.nb_ratings = {}
        for (user_id, work_id), rating in zip(X, y):
            if not user_id in self.ratings:
                self.ratings[user_id] = {}
            if not work_id in self.nb_ratings:
                self.nb_ratings[work_id] = 1
                self.sum_ratings[work_id] = rating
            self.ratings[user_id][work_id] = rating
            self.nb_ratings[work_id] += 1
            self.sum_ratings[work_id] = rating

        for work_id in self.nb_ratings:
            self.mean_score[work_id] = self.sum_ratings[work_id] / self.nb_ratings[work_id]

    def predict(self, X):
        y = []
        for my_user_id, work_id in X:
            if not my_user_id in self.closest_neighbors:
                self.get_neighbors(my_user_id)
            weight = 0
            predicted_rating = 0
            for user_id in self.closest_neighbors[my_user_id]:
                their_sim_score = self.closest_neighbors[my_user_id][user_id]
                their_rating = self.ratings[user_id].get(work_id, self.mean_score[work_id])
                predicted_rating += their_sim_score * their_rating
                weight += their_sim_score
            predicted_rating /= weight
            y.append(predicted_rating)
        return np.array(y)

    def __str__(self):
        return '[KNN] NB_NEIGHBORS = %d' % self.NB_NEIGHBORS

    def get_shortname(self):
        return 'knn-%d' % self.NB_NEIGHBORS
