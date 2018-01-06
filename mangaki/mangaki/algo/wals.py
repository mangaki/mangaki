from collections import defaultdict, Counter

import numpy as np

from mangaki.algo.recommendation_algorithm import RecommendationAlgorithm, register_algorithm


def simple_train(model, inp, num_iterations):
    """Helper function to train model on inp for num_iterations."""
    row_update_op = model.update_row_factors(sp_input=inp)[1]
    col_update_op = model.update_col_factors(sp_input=inp)[1]

    model.initialize_op.run()
    model.worker_init.run()
    for _ in range(num_iterations):
        model.row_update_prep_gramian_op.run()
        model.initialize_row_update_op.run()
        row_update_op.run()
        model.col_update_prep_gramian_op.run()
        model.initialize_col_update_op.run()
        col_update_op.run()


@register_algorithm('wals', {'nb_components': 20})
class MangakiWALS(RecommendationAlgorithm):
    M = None
    U = None
    V = None

    def __init__(self, nb_components=20):
        """An implementation of the Weighted Alternate Least Squares.
        NB_COMPONENTS: the number of components in the factorization"""
        super().__init__()
        self.nb_components = nb_components

    def load(self, filename):
        backup = super().load(filename)
        self.M = backup.M
        self.U = backup.U
        self.V = backup.V
        self.means = backup.means

    @property
    def is_serializable(self):
        return True

    def make_matrix(self, X, y):
        matrix = defaultdict(dict)
        nb_ratings = Counter()
        means = np.zeros((self.nb_users,))
        users = set()
        for (user, work), rating in zip(X, y):
            matrix[(user, work)] = rating
            means[user] += rating
            nb_ratings[user] += 1
            users.add(user)
        for user in users:
            means[user] /= nb_ratings[user]
        indices = []
        values = []
        for (user, work) in X:
            matrix[(user, work)] -= means[user]
            indices.append((user, work))
            values.append(matrix[(user, work)])
        return indices, values, means

    def factorize(self, indices, values):
        import tensorflow as tf
        from tensorflow.contrib.factorization.python.ops import factorization_ops
        from tensorflow.python.framework import sparse_tensor

        rows = self.nb_users
        cols = self.nb_works
        dims = self.nb_components
        row_wts = 0.1 + np.random.rand(rows)
        col_wts = 0.1 + np.random.rand(cols)
        inp = sparse_tensor.SparseTensor(indices, values, [rows, cols])
        use_factors_weights_cache = True
        model = factorization_ops.WALSModel(
            rows,
            cols,
            dims,
            unobserved_weight=1,  # .1,
            regularization=0.001,  # 001,
            row_weights=None,  # row_wts,
            col_weights=None,  # col_wts,
            use_factors_weights_cache=use_factors_weights_cache)
        tf.InteractiveSession()
        simple_train(model, inp, 25)
        row_factor = model.row_factors[0].eval()
        self.U = row_factor
        col_factor = model.col_factors[0].eval()
        self.V = col_factor

    def fit(self, X, y):
        print("Computing M: (%i × %i)" % (self.nb_users, self.nb_works))
        indices, values, self.means = self.make_matrix(X, y)

        self.chrono.save('fill and center matrix')

        self.factorize(indices, values)

        self.chrono.save('factor matrix')

    def unzip(self):
        self.chrono.save('begin of fit')
        self.M = self.U.dot(self.V.T)
        self.chrono.save('end of fit')

    def predict(self, X):
        if self.M is not None:  # Model is unzipped
            M = self.M
        else:
            M = self.U.dot(self.V.T)
        return M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)] + self.means[X[:, 0].astype(np.int64)]

    def get_shortname(self):
        return 'wals'
