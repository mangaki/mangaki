from django.contrib.auth.models import User
from mangaki.utils.values import rating_values
from collections import Counter
from math import sqrt
import numpy as np
from scipy.sparse import lil_matrix


class MangakiKNN(object):
    NB_NEIGHBORS = None
    closest_neighbors = None
    rated_works = None
    mean_score = None
    ratings = None
    sum_ratings = None
    nb_ratings = None
    M = None
    def __init__(self, NB_NEIGHBORS=15):
        self.NB_NEIGHBORS = NB_NEIGHBORS
        self.closest_neighbors = {}
        self.rated_works = {}
        self.mean_score = {}
        self.ratings = {}
        self.sum_ratings = {}
        self.nb_ratings = {}

    def set_parameters(self, nb_users, nb_works):
        self.nb_users = nb_users
        self.nb_works = nb_works

    def get_similarity(self, my_user_id, user_id):
        score = 0
        for work_id in self.rated_works & set(self.ratings[user_id].keys()):
            score += self.ratings[my_user_id][work_id] * self.ratings[user_id][work_id]
        return score

    def get_similarity2(self, my_user_id, user_id):
        score = self.get_similarity(my_user_id, user_id)
        my_norm = sqrt(self.get_similarity(my_user_id, my_user_id))
        their_norm = sqrt(self.get_similarity(user_id, user_id))
        if my_norm and their_norm:
            score /= (my_norm * their_norm)
        return score

    def get_neighbors(self, my_user_id, normalized=False):
        if normalized:
            similarity_f = self.get_similarity2
        else:
            similarity_f = self.get_similarity
        neighbors = Counter()
        
        if my_user_id in self.ratings:
            self.rated_works = set(self.ratings[my_user_id].keys())
            for user_id in self.ratings:
                if user_id != my_user_id:    
                    neighbors[user_id] = similarity_f(my_user_id, user_id)

        self.closest_neighbors[my_user_id] = {}
        # users = []
        for user_id, sim_score in neighbors.most_common(self.NB_NEIGHBORS):
            self.closest_neighbors[my_user_id][user_id] = sim_score
            # users.append(User.objects.get(id=user_id).username)
        print(self.closest_neighbors[my_user_id])
        # return users

    def get_all_neighbors(self):
        score = self.M.dot(self.M.transpose())
        for user_id in range(self.nb_users):
            self.closest_neighbors[user_id] = {}
            for neighbor_id in score[user_id].toarray()[0].argpartition(-self.NB_NEIGHBORS - 1)[-self.NB_NEIGHBORS - 1:-1]:
                self.closest_neighbors[user_id][neighbor_id] = score[user_id, neighbor_id]

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

    def fit(self, X=[], y=[], all_dataset=False):
        if all_dataset:
            for user_id, work_id, choice in Rating.objects.values_list('user_id', 'work_id', 'choice'):
                X.append((user_id, work_id))
                y.append(rating_values[choice])
        self.ratings = {}
        self.sum_ratings = {}
        self.nb_ratings = {}
        self.M = lil_matrix((self.nb_users, self.nb_works))
        for (user_id, work_id), rating in zip(X, y):
            if not user_id in self.ratings:
                self.ratings[user_id] = {}
            if not work_id in self.nb_ratings:
                self.nb_ratings[work_id] = 1
                self.sum_ratings[work_id] = rating
            self.ratings[user_id][work_id] = rating
            self.nb_ratings[work_id] += 1
            self.sum_ratings[work_id] = rating
            self.M[user_id, work_id] = rating
        for work_id in self.nb_ratings:
            self.mean_score[work_id] = self.sum_ratings[work_id] / self.nb_ratings[work_id]
        self.get_all_neighbors()

    def predict(self, X):
        y = []
        for my_user_id, work_id in X:
            """if not my_user_id in self.closest_neighbors:
                self.get_neighbors(my_user_id)"""
            weight = 0
            predicted_rating = 0
            for user_id in self.closest_neighbors[my_user_id]:
                their_sim_score = self.closest_neighbors[my_user_id][user_id]
                their_rating = self.ratings[user_id].get(work_id, self.mean_score.get(work_id, 0))  # Double fallback
                predicted_rating += their_sim_score * their_rating
                weight += their_sim_score
            if weight > 0:
                predicted_rating /= weight
            y.append(predicted_rating)
        return np.array(y)

    def __str__(self):
        return '[KNN] NB_NEIGHBORS = %d' % self.NB_NEIGHBORS

    def get_shortname(self):
        return 'knn-%d' % self.NB_NEIGHBORS
