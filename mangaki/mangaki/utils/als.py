from collections import defaultdict
from mangaki.utils.chrono import Chrono
import numpy as np
import pickle

class MangakiALS(object):
    M = None
    U = None
    VT = None
    def __init__(self, NB_COMPONENTS=10, NB_ITERATIONS=10, LAMBDA=0.1):
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
        self.means = backup.means

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
        Gi = self.LAMBDA  * len(matrixT[work]) * np.eye(self.NB_COMPONENTS)
        self.VT[:,[work]] = np.linalg.solve(Ui.dot(Ui.T) + Gi, Ui.dot(Ri))

    def factorize(self, matrix, random_state):
        # Preprocessings
        matrixT = defaultdict(dict)
        for user in matrix:
            for work in matrix[user]:
                matrixT[work][user] = matrix[user][work]
        # Init
        self.U = np.random.rand(self.nb_users, self.NB_COMPONENTS)
        self.VT = np.random.rand(self.NB_COMPONENTS, self.nb_works)
        # ALS
        for i in range(self.NB_ITERATIONS):
            #print('Step {}'.format(i))
            for user in matrix:
                self.fit_user(user, matrix)
            for work in matrixT:
                self.fit_work(work, matrixT)

    def fit(self, X, y):
        print("Computing M: (%i × %i)" % (self.nb_users, self.nb_works))
        matrix, self.means = self.make_matrix(X, y)

        self.chrono.save('fill and center matrix')

        self.factorize(matrix, random_state=42)
        print('Shapes', self.U.shape, self.VT.shape)
        self.M = self.U.dot(self.VT)

        #self.save('backup.pickle')

        self.chrono.save('factor matrix')

    def predict(self, X):
        return self.M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)] + self.means[X[:, 0].astype(np.int64)]

    def __str__(self):
        return '[ALS]'

    def get_shortname(self):
        return 'als'
