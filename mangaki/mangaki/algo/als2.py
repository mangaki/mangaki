from mangaki.algo.recommendation_algorithm import RecommendationAlgorithm, register_algorithm
from collections import defaultdict
import numpy as np


@register_algorithm('als2', {'nb_components': 20})
class MangakiALS2(RecommendationAlgorithm):
    '''
    Alternating Least Squares for "Singular Value Decomposition" model (aka latent factor model)
    r_{ij} - mean = bias_i + bias_j + u_i^T v_j
    Modified version of ALS for the SVD model
    Ratings are preprocessed by removing the overall mean
    Then (u_i and bias_i), (v_j and bias_j) are updated alternatively in closed form

    ALS:
    Zhou, Yunhong, et al. "Large-scale parallel collaborative filtering for the netflix prize." International Conference on Algorithmic Applications in Management. Springer, Berlin, Heidelberg, 2008.
    http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.173.2797&rep=rep1&type=pdf

    SVD:
    Koren, Yehuda, and Robert Bell. "Advances in collaborative filtering." Recommender systems handbook. Springer, Boston, MA, 2015. 77-118.
    https://pdfs.semanticscholar.org/6800/fbe3314be9f638fb075e15b489d1aadb3030.pdf
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
        for user in matrix.keys():
            means[user] /= len(matrix[user])
        return matrix, means

    def fit_user(self, user, matrix):
        Ru = np.array(list(matrix[user].values()))
        Ju = list(matrix[user].keys())
        Wu = self.W_item[Ju]
        wu = self.w + self.W_user[user]
        Vu = self.VT[:, Ju]
        Gu = self.lambda_ * len(matrix[user]) * np.eye(self.nb_components)
        self.U[[user],:] = np.linalg.solve(Vu.dot(Vu.T) + Gu, Vu.dot(Ru - Wu - wu)).T
        self.W_user[user] = (Ru - Vu.T.dot(self.U[user, :]) - Wu).mean() / (1 + self.lambda_) - self.w

    def fit_work(self, work, matrixT):
        Ri = np.array(list(matrixT[work].values()))
        Ii = list(matrixT[work].keys())
        Wi = self.W_user[Ii]
        wi = self.w + self.W_item[work]
        Ui = self.U[Ii, :].T
        Gi = self.lambda_ * len(matrixT[work]) * np.eye(self.nb_components)
        self.VT[:,[work]] = np.linalg.solve(Ui.dot(Ui.T) + Gi, Ui.dot(Ri - Wi - wi).reshape(-1, 1))
        self.W_item[work] = (Ri - Ui.T.dot(self.VT[:, work]) - Wi).mean() / (1 + self.lambda_) - self.w

    def factorize(self, matrix, random_state):
        # Preprocessings
        matrixT = defaultdict(dict)
        for user in matrix:
            for work in matrix[user]:
                matrixT[work][user] = matrix[user][work]
        # Init
        self.U = np.random.rand(self.nb_users, self.nb_components)
        self.VT = np.random.rand(self.nb_components, self.nb_works)
        self.w = 0.
        self.W_user = np.random.rand(self.nb_users)
        self.W_item = np.random.rand(self.nb_works)
        # ALS
        for i in range(self.nb_iterations):
            for user in matrix:
                self.fit_user(user, matrix)
            for work in matrixT:
                self.fit_work(work, matrixT)

    def fit(self, X, y):
        if self.verbose_level:
            print("Computing M: (%i × %i)" % (self.nb_users, self.nb_works))
        self.w = y.mean()
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
        users = X[:, 0].astype(np.int64)
        works = X[:, 1].astype(np.int64)
        return M[users, works] + self.W_user[users] + self.W_item[works] + self.w

    def get_shortname(self):
        return 'als2-%d' % self.nb_components
