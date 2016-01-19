from django.contrib.auth.models import User
from mangaki.models import Rating, Work, Recommendation
from mangaki.utils.chrono import Chrono
from mangaki.utils.values import rating_values
from scipy.sparse import lil_matrix
from sklearn.utils.extmath import randomized_svd
import numpy as np
from django.db import connection
import pickle
import json
import math

NB_COMPONENTS = 10
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
    def __init__(self):
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

    def fit(self, X, y):
        self.work_titles = {}
        for work in Work.objects.values('id', 'title'):
            self.work_titles[work['id']] = work['title']
        
        work_ids = list(Rating.objects.values_list('work_id', flat=True).distinct())
        nb_works = len(work_ids)
        self.inv_work = {work_ids[i]: i for i in range(nb_works)}

        user_ids = list(User.objects.values_list('id', flat=True))
        nb_users = len(user_ids)
        self.inv_user = {user_ids[i]: i for i in range(nb_users)}

        self.chrono.save('get_work_ids')

        # print("Computing M: (%i × %i)" % (nb_users, nb_works))
        self.M = lil_matrix((nb_users, nb_works))
        """ratings_of = {}
        for (user_id, work_id), rating in zip(X, y):
            ratings_of.setdefault(user_id, []).append(rating)"""
        for (user_id, work_id), rating in zip(X, y):
            self.M[self.inv_user[user_id], self.inv_work[work_id]] = rating #- np.mean(ratings_of[user_id])
        # np.save('backupM', self.M)

        self.chrono.save('fill matrix')

        # Ranking computation
        self.U, self.sigma, self.VT = randomized_svd(self.M, NB_COMPONENTS, n_iter=3, random_state=42)
        # print('Formes', self.U.shape, self.sigma.shape, self.VT.shape)

        self.save('backup.pickle')

        self.chrono.save('factor matrix')

    def predict(self, X):
        y = []
        for user_id, work_id in X:
            i = self.inv_user[user_id]
            j = self.inv_work[work_id]
            y.append(self.U[i].dot(np.diag(self.sigma)).dot(self.VT.transpose()[j]))
        return np.array(y)

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
