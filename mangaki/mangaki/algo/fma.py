import numpy as np
import pywFM
import os
from scipy.sparse import coo_matrix

from mangaki.algo.recommendation_algorithm import (RecommendationAlgorithm,
                                                   register_algorithm)


@register_algorithm('fma', {'rank': 20})
class MangakiFMA(RecommendationAlgorithm):
    def __init__(self, rank=20, nb_iterations=10):
        super().__init__()
        self.rank = rank
        self.nb_iterations = nb_iterations
        self.fm = None

    def load(self, filename):
        backup = super().load(filename)
        self.mu = backup.mu
        self.W = backup.W
        self.V = backup.V
        self.V2 = backup.V2

    @property
    def is_serializable(self):
        return True

    def prepare_fm(self, X):
        nb_samples = len(X)
        user_ids = X[:, 0]
        work_ids = X[:, 1]
        # For the k-th user_id-work_id pair, we need (k, user_id) and (k, N + work_id), so two copies of range(nb_samples)
        rows = list(range(nb_samples)) * 2
        cols = np.concatenate((user_ids, self.nb_users + work_ids))
        X_fm = coo_matrix(([1] * (2 * nb_samples), (rows, cols)),
                          shape=(nb_samples, self.nb_users + self.nb_works)
                          ).tocsr()
        return X_fm

    def fit(self, X, y):
        X_fm = self.prepare_fm(X)
        self.chrono.save('prepare data in sparse FM format')

        os.environ['LIBFM_PATH'] = 'XXX'  # If applicable
        fm = pywFM.FM(task='regression', num_iter=self.nb_iterations, k2=self.rank, rlog=False)  # MCMC method
        model = fm.run(X_fm, y, X_fm, y)
        self.chrono.save('train FM')

        nb_agents = self.nb_users + self.nb_works
        current = len(model.weights)

        if model.global_bias is None:  # Train failed (for example, libfm does not exist)
            self.mu = 0
            self.W = np.random.random(nb_agents)
            self.V = np.random.random((nb_agents, self.rank))
        else:
            self.mu = model.global_bias
            self.W = np.pad(np.array(model.weights), (0, nb_agents - current), mode='constant')  # Just in case X_fm had too many zero columns on the right
            self.V = np.pad(model.pairwise_interactions, [(0, nb_agents - current), (0, 0)], mode='constant')
        self.V2 = np.power(self.V, 2)

    def predict(self, X):
        X_fm = self.prepare_fm(X)
        return self.mu + X_fm.dot(self.W) + 0.5 * (np.linalg.norm(X_fm.dot(self.V), axis=1) ** 2 - X_fm.dot(self.V2).sum(axis=1))

    def get_shortname(self):
        return 'fma-%d' % self.rank
