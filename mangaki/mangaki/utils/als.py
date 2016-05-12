from collections import defaultdict
from django.contrib.auth.models import User
from mangaki.models import Rating, Work, Recommendation
from mangaki.utils.chrono import Chrono
from mangaki.utils.values import rating_values
import numpy as np
from django.db import connection
import pickle
import json
import math

TOP = 10


class MangakiALS(object):
    M = None
    U = None
    VT = None
    def __init__(self, NB_COMPONENTS=10, NB_ITERATIONS=10, LAMBDA=10):
        self.NB_COMPONENTS = NB_COMPONENTS
        self.NB_ITERATIONS = NB_ITERATIONS
        self.LAMBDA = LAMBDA
        self.chrono = Chrono(True)

    def save(self, filename):
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

    def load(self, filename):
        with open(filename, 'rb') as f:
            backup = pickle.load(f)
        self.M = backup.M
        self.U = backup.U
        self.VT = backup.VT

    def set_parameters(self, nb_users, nb_works):
        self.nb_users = nb_users
        self.nb_works = nb_works

    def make_matrix(self, X, y):
        matrix = defaultdict(dict)
        means = np.zeros((self.nb_users,))
        for (user, work), rating in zip(X, y):
            matrix[user][work] = rating
            means[user] += rating
        for user in matrix:
            means[user] /= len(matrix[user])
        for (user, work) in X:
            matrix[user][work] -= means[user]
        return matrix, means

    def fit_user(self, user, matrix):
        Ru = np.array(list(matrix[user].values()), ndmin=2).T
        Vu = self.VT[:,list(matrix[user].keys())]
        Gu = self.LAMBDA * len(matrix[user]) * np.eye(self.NB_COMPONENTS)
        self.U[[user],:] = np.linalg.solve(Vu.dot(Vu.T) + Gu, Vu.dot(Ru)).T

    def fit_work(self, work, matrixT):
        Ri = np.array(list(matrixT[work].values()), ndmin=2).T
        Ui = self.U[list(matrixT[work].keys()),:].T
        Gi = self.LAMBDA * len(matrixT[work]) * np.eye(self.NB_COMPONENTS)
        self.VT[:,[work]] = np.linalg.solve(Ui.dot(Ui.T) + Gi, Ui.dot(Ri))

    def svd(self, matrix, random_state):
        # Init
        np.random.seed(random_state);
        self.U = np.random.rand(self.nb_users, self.NB_COMPONENTS)
        self.VT = np.random.rand(self.NB_COMPONENTS, self.nb_works)
        # Preprocessings
        matrixT = defaultdict(dict)
        for user in matrix:
            for work in matrix[user]:
                matrixT[work][user] = matrix[user][work]
        # ALS
        for i in range(self.NB_ITERATIONS):
            print('Step {}'.format(i))
            for user in matrix:
                self.fit_user(user, matrix)
            for work in matrixT:
                self.fit_work(work, matrixT)

    def fit(self, X, y):
        print("Computing M: (%i × %i)" % (self.nb_users, self.nb_works))
        matrix, self.means = self.make_matrix(X, y)

        self.chrono.save('fill and center matrix')

        # SVD
        self.svd(matrix, random_state=42)
        print('Shapes', self.U.shape, self.VT.shape)
        self.M = self.U.dot(self.VT)

        #self.save('backup.pickle')

        self.chrono.save('factor matrix')

    def predict(self, X):
        return self.M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)] + self.means[X[:, 0].astype(np.int64)]

    def get_reco(self, username, sending=False):
        target_user = User.objects.get(username=username)
        the_user_id = target_user.id
        svd_user = User.objects.get(username='svd')

        work_ids = {self.inv_work[work_id]: work_id for work_id in self.inv_work}
        nb_works = len(work_ids)

        seen_works = set(Rating.objects.filter(user__id=the_user_id).exclude(choice='willsee').values_list('work_id', flat=True))
        the_i = self.inv_user[the_user_id]

        self.chrono.save('get_seen_works')

        print('mon vecteur (taille %d)' % len(self.U[the_i]), self.U[the_i])
        print(self.sigma)
        for i, line in enumerate(self.VT):
            print('=> Ligne %d' % (i + 1), '(ma note : %f)' % self.U[the_i][i])
            sorted_line = sorted((line[j], self.work_titles[work_ids[j]]) for j in range(nb_works))[::-1]
            top5 = sorted_line[:10]
            bottom5 = sorted_line[-10:]
            for anime in top5:
                print(anime)
            for anime in bottom5:
                print(anime)
            """if i == 0 or i == 1:  # First two vectors explaining variance
                with open('vector%d.json' % (i + 1), 'w') as f:
                    vi = X.dot(line).tolist()
                    x_norm = [np.dot(X.data[k], X.data[k]) / (nb_works + 1) for k in range(nb_users + 1)]
                    f.write(json.dumps({'v': [v / math.sqrt(x_norm[k]) if x_norm[k] != 0 else float('inf') for k, v in enumerate(vi)]}))"""
        # print(VT.dot(VT.transpose()))
        # return

        the_ratings = self.predict((the_user_id, work_ids[j]) for j in range(nb_works))
        ranking = sorted(zip(the_ratings, [(work_ids[j], self.work_titles[work_ids[j]]) for j in range(nb_works)]), reverse=True)

        # Summarize the results of the ranking for the_user_id:
        # “=> rank, title, score”
        c = 0
        for i, (rating, (work_id, title)) in enumerate(ranking, start=1):
            if work_id not in seen_works:
                print('=>', i, title, rating, self.predict([(the_user_id, work_id)]))
                if Recommendation.objects.filter(user=svd_user, target_user__id=the_user_id, work__id=work_id).count() == 0:
                    Recommendation.objects.create(user=svd_user, target_user_id=the_user_id, work_id=work_id)
                c += 1
            elif i < TOP:
                print(i, title, rating)
            if c >= TOP:
                break

        """print(len(connection.queries), 'queries')
        for line in connection.queries:
            print(line)"""

        self.chrono.save('complete')

    def __str__(self):
        return '[ALS]'

    def get_shortname(self):
        return 'als'
