from collections import defaultdict

import numpy as np
from .recommendation_algorithm import RecommendationAlgorithm, register_algorithm


@register_algorithm('xals')
class MangakiXALS(RecommendationAlgorithm):
    M = None
    U = None
    VT = None
    def __init__(self, nb_components=10, nb_iterations=10, lambda_=0.1):
        super().__init__()
        self.nb_components = nb_components
        self.nb_iterations = nb_iterations
        self.lambda_ = lambda_

    @property
    def is_serializable(self):
        return True

    def load(self, filename):
        backup = super().load(filename)
        self.M = backup.M
        self.U = backup.U
        self.VT = backup.VT
        self.means = backup.means

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
        Vu = self.VT[:, list(matrix[user].keys())]
        Gu = self.lambda_ * len(matrix[user]) * np.eye(self.nb_components + self.nb_tags)
        self.U[[user], :] = np.linalg.solve(Vu.dot(Vu.T) + Gu, Vu.dot(Ru)).T

    def fit_work(self, work, matrixT):
        Ri = np.array(list(matrixT[work].values()), ndmin=2).T
        Ui = self.U[list(matrixT[work].keys()), :].T
        Gi = self.lambda_ * len(matrixT[work]) * np.eye(self.nb_components + self.nb_tags)
        Pi = Ui[-self.nb_tags:, :]
        Ti = self.T[work]
        newV = np.linalg.solve(Ui.dot(Ui.T) + Gi, Ui.dot(Ri - Ti.dot(Pi)))
        self.VT[:self.nb_components, work] = newV[:self.nb_components, 0]

    def factorize(self, matrix, random_state):
        # Preprocessings
        matrixT = defaultdict(dict)
        for user in matrix:
            for work in matrix[user]:
                matrixT[work][user] = matrix[user][work]
        # Init
        self.U = np.random.rand(self.nb_users, self.nb_components + self.nb_tags)
        self.VT = np.concatenate((np.random.rand(self.nb_components, self.nb_works), self.T.T))
        # ALS
        for i in range(self.nb_iterations):
            self.M = self.U.dot(self.VT)
            #print('shape X_train', self.X_train.shape)
            y_pred = self.predict(self.X_train)
            print('Step {}: {}'.format(i, self.compute_rmse(self.predict(self.X_train), self.y_train)))
            for user in matrix:
                self.fit_user(user, matrix)
            for work in matrixT:
                self.fit_work(work, matrixT)

    def fit(self, X, y):
        self.X_train = X
        self.y_train = y
        if self.verbose_level:
            print("Computing M: (%i × %i)" % (self.nb_users, self.nb_works))
        matrix, self.means = self.make_matrix(X, y)

        self.chrono.save('fill and center matrix')

        self.factorize(matrix, random_state=42)
        if self.verbose_level:
            print('Shapes', self.U.shape, self.VT.shape)
        self.M = self.U.dot(self.VT)

        #self.save('backup.pickle')

        self.chrono.save('factor matrix')

    def predict(self, X):
        return self.M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)] + self.means[X[:, 0].astype(np.int64)]

    def get_shortname(self):
        return 'xals-%d' % self.nb_components
