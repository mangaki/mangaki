import numpy as np
from sklearn.decomposition import PCA

from mangaki.algo.recommendation_algorithm import RecommendationAlgorithm


class MangakiPCA(RecommendationAlgorithm):
    M = None
    def __init__(self, NB_COMPONENTS=10):
        super().__init__()
        self.NB_COMPONENTS = NB_COMPONENTS
        self.VT = None

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
        pca = PCA(n_components=self.NB_COMPONENTS)
        matrix, self.means = self.make_matrix(X, y)
        pca.fit(matrix)
        self.components_ = pca.components_
        self.VT = pca.components_
        self.M = pca.transform(matrix).dot(np.diag(np.sqrt(pca.explained_variance_ / self.nb_users))).dot(pca.components_)

    def predict(self, X):
        return self.M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)] + self.means[X[:, 0].astype(np.int64)]

    def get_shortname(self):
        return 'pca'
