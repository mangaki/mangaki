import numpy as np
from fastFM import als
from scipy.sparse import coo_matrix

from mangaki.algo.recommendation_algorithm import (RecommendationAlgorithm,
                                                   register_algorithm)


@register_algorithm('cfm', {'rank': 20})
class MangakiCFM(RecommendationAlgorithm):
    def __init__(self, rank=20, nb_iterations=10):
        super().__init__()
        self.rank = rank
        self.nb_iterations = nb_iterations

    def load(self, filename):
        backup = super().load(filename)
        # Would need to use als.set_params, fed with als.get_params

    @property
    def is_serializable(self):
        return False  # Not yet

    def prepare_fm(self, X):
        nb_samples = len(X)
        user_ids = X[:, 0]
        work_ids = X[:, 1]
        rows = list(range(nb_samples))
        rows += rows
        cols = np.concatenate((user_ids, self.nb_users + work_ids))
        X_fm = coo_matrix(([1] * (2 * nb_samples), (rows, cols)),
                          shape=(nb_samples, self.nb_users + self.nb_works)
                          ).tocsc()
        return X_fm

    def fit(self, X, y):
        X_fm = self.prepare_fm(X)

        self.chrono.save('prepare data in sparse FM format')

        self.fm = als.FMRegression(n_iter=10, rank=self.rank)
        self.fm.fit(X_fm, y)

        self.chrono.save('factor matrix')

    def predict(self, X):
        X_fm = self.prepare_fm(X)
        return self.fm.predict(X_fm)

    def get_shortname(self):
        return 'cfm-%d' % self.rank
