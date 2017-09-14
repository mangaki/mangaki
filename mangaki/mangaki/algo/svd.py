import numpy as np
from sklearn.utils.extmath import randomized_svd

from mangaki.algo.recommendation_algorithm import RecommendationAlgorithm, register_algorithm


@register_algorithm('svd', {'nb_components': 20})
class MangakiSVD(RecommendationAlgorithm):
    M = None
    U = None
    sigma = None
    VT = None
    def __init__(self, nb_components=20, nb_iterations=10):
        super().__init__()
        self.nb_components = nb_components
        self.nb_iterations = nb_iterations

    def load(self, filename):
        backup = super().load(filename)
        self.M = backup.M
        self.U = backup.U
        self.sigma = backup.sigma
        self.VT = backup.VT
        self.means = backup.means

    @property
    def is_serializable(self):
        return True

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
        if self.verbose_level:
            print("Computing M: (%i × %i)" % (self.nb_users, self.nb_works))
        matrix, self.means = self.make_matrix(X, y)

        self.chrono.save('fill and center matrix')

        self.U, self.sigma, self.VT = randomized_svd(matrix, self.nb_components, n_iter=self.nb_iterations, random_state=42)
        if self.verbose_level:
            print('Shapes', self.U.shape, self.sigma.shape, self.VT.shape)

        self.chrono.save('factor matrix')

    def unzip(self):
        self.chrono.save('begin of fit')
        self.M = self.U.dot(np.diag(self.sigma)).dot(self.VT)
        self.chrono.save('end of fit')

    def predict(self, X):
        if self.M is not None:  # Model is unzipped
            M = self.M
        else:
            M = self.U.dot(np.diag(self.sigma)).dot(self.VT)
        return M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)] + self.means[X[:, 0].astype(np.int64)]

    def get_shortname(self):
        return 'svd-%d' % self.nb_components
