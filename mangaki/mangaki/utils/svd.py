import pickle

import numpy as np
from django.contrib.auth.models import User
from sklearn.utils.extmath import randomized_svd

from mangaki.models import Rating, Recommendation
from mangaki.utils.chrono import Chrono

TOP = 10


class MangakiSVD(object):
    M = None
    U = None
    sigma = None
    VT = None
    chrono = None
    inv_work = None
    inv_user = None
    work_titles = None
    def __init__(self, NB_COMPONENTS=10, NB_ITERATIONS=10):
        self.NB_COMPONENTS = NB_COMPONENTS
        self.NB_ITERATIONS = NB_ITERATIONS
        self.chrono = Chrono(True)

    def save(self, filename):
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

    def load(self, filename):
        with open(filename, 'rb') as f:
            backup = pickle.load(f)
        self.M = backup.M
        self.U = backup.U
        self.sigma = backup.sigma
        self.VT = backup.VT
        self.inv_work = backup.inv_work
        self.inv_user = backup.inv_user
        self.work_titles = backup.work_titles
        self.means = backup.means

    def set_parameters(self, nb_users, nb_works):
        self.nb_users = nb_users
        self.nb_works = nb_works

    def make_matrix(self, X, y):
        matrix = np.zeros((self.nb_users, self.nb_works), dtype=np.float64)
        for (user, work), rating in zip(X, y):
            matrix[user][work] = rating
        means = np.zeros((self.nb_users,))
        for i in range(self.nb_users):
            means[i] = np.sum(matrix[i]) / np.sum(matrix[i] != 0)
            if np.isnan(means[i]):
                means[i] = 0
            matrix[i][matrix[i] != 0] -= means[i]
        return matrix, means

    def fit(self, X, y):
        print("Computing M: (%i × %i)" % (self.nb_users, self.nb_works))
        matrix, self.means = self.make_matrix(X, y)

        self.chrono.save('fill and center matrix')

        self.U, self.sigma, self.VT = randomized_svd(matrix, self.NB_COMPONENTS, n_iter=self.NB_ITERATIONS, random_state=42)
        print('Shapes', self.U.shape, self.sigma.shape, self.VT.shape)
        self.M = self.U.dot(np.diag(self.sigma)).dot(self.VT)

        self.save('backup.pickle')

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
        return '[SVD]'

    def get_shortname(self):
        return 'svd'
