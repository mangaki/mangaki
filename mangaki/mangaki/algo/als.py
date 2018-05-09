from mangaki.algo.recommendation_algorithm import RecommendationAlgorithm, register_algorithm
from collections import defaultdict
import numpy as np


@register_algorithm('als', {'nb_components': 20})
class MangakiALS(RecommendationAlgorithm):
    '''
    Alternating Least Squares
    r_{ij} - mean_i = u_i^T v_j
    Ratings are preprocessed by removing the mean rating of each user
    Then u_i and v_j are updated alternatively, using the least squares estimator (closed form)

    ALS:
    Zhou, Yunhong, et al. "Large-scale parallel collaborative filtering for the netflix prize." International Conference on Algorithmic Applications in Management. Springer, Berlin, Heidelberg, 2008.
    http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.173.2797&rep=rep1&type=pdf

    Implemented by Pierre Vigier, JJ Vie
    '''
    M = None
    U = None
    VT = None
    def __init__(self, nb_components=20, nb_iterations=20, lambda_=0.1):
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
        Vu = self.VT[:,list(matrix[user].keys())]
        Gu = self.lambda_ * len(matrix[user]) * np.eye(self.nb_components)
        self.U[[user],:] = np.linalg.solve(Vu.dot(Vu.T) + Gu, Vu.dot(Ru)).T

    def fit_work(self, work, matrixT):
        Ri = np.array(list(matrixT[work].values()), ndmin=2).T
        Ui = self.U[list(matrixT[work].keys()),:].T
        Gi = self.lambda_ * len(matrixT[work]) * np.eye(self.nb_components)
        self.VT[:,[work]] = np.linalg.solve(Ui.dot(Ui.T) + Gi, Ui.dot(Ri))

    def factorize(self, matrix, random_state):
        # Preprocessings
        matrixT = defaultdict(dict)
        for user in matrix:
            for work in matrix[user]:
                matrixT[work][user] = matrix[user][work]
        # Init
        self.U = np.random.rand(self.nb_users, self.nb_components)
        self.VT = np.random.rand(self.nb_components, self.nb_works)
        # ALS
        for i in range(self.nb_iterations):
            for user in matrix:
                self.fit_user(user, matrix)
            for work in matrixT:
                self.fit_work(work, matrixT)

    def fit(self, X, y):
        if self.verbose_level:
            print("Computing M: (%i × %i)" % (self.nb_users, self.nb_works))
        matrix, self.means = self.make_matrix(X, y)

        self.chrono.save('fill and center matrix')

        self.factorize(matrix, random_state=42)
        if self.verbose_level:
            print('Shapes', self.U.shape, self.VT.shape)

        self.chrono.save('factor matrix')

    def unzip(self):
        self.chrono.save('begin of fit')
        self.M = self.U.dot(self.VT)
        self.chrono.save('end of fit')

    def predict(self, X):
        if self.M is not None:  # Model is unzipped
            M = self.M
        else:
            M = self.U.dot(self.VT)
        return M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)] + self.means[X[:, 0].astype(np.int64)]

    def get_shortname(self):
        return 'als-%d' % self.nb_components
