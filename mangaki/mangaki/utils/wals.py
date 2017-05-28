from mangaki.utils.common import RecommendationAlgorithm
from collections import defaultdict, Counter
import numpy as np
from sklearn.externals import joblib


def simple_train(sess, model, inp, num_iterations):
    """Helper function to train model on inp for num_iterations."""
    row_update_op = model.update_row_factors(sp_input=inp)[1]
    col_update_op = model.update_col_factors(sp_input=inp)[1]

    model.initialize_op.run(session=sess)
    model.worker_init.run(session=sess)
    for _ in range(num_iterations):
        model.row_update_prep_gramian_op.run(session=sess)
        model.initialize_row_update_op.run(session=sess)
        row_update_op.run(session=sess)
        model.col_update_prep_gramian_op.run(session=sess)
        model.initialize_col_update_op.run(session=sess)
        col_update_op.run(session=sess)


class MangakiWALS(RecommendationAlgorithm):
    M = None

    def __init__(self, NB_COMPONENTS=20):
        """An implementation of the Weighted Alternate Least Squares.
        NB_COMPONENTS: the number of components in the factorization"""
        import tensorflow as tf

        super().__init__()
        self.NB_COMPONENTS = NB_COMPONENTS
        self.tf = tf
        self.sess = tf.Session()

    def load(self, filename):
        results = joblib.load(self.get_backup_path(filename))
        self.M = results['M']
        self.means = results['means']

    def save(self, filename):
        joblib.dump({
            'means': self.means,
            'M': self.M
        }, self.get_backup_path(filename))

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
        from tensorflow.contrib.factorization.python.ops import factorization_ops
        from tensorflow.python.framework import sparse_tensor

        weights = self.tf.Variable(values, name='weights')
        init_op = self.tf.global_variables_initializer()

        rows = self.nb_users
        cols = self.nb_works
        dims = self.NB_COMPONENTS
        row_wts = 0.1 + np.random.rand(rows)
        col_wts = 0.1 + np.random.rand(cols)
        self.sess.run(init_op)

        inp = sparse_tensor.SparseTensor(indices, self.tf.identity(weights), [rows, cols])
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
        simple_train(self.sess, model, inp, 25)
        row_factor = self.sess.run(model.row_factors[0])
        print('Shape', row_factor.shape)
        col_factor = self.sess.run(model.col_factors[0])
        print('Shape', col_factor.shape)
        # Dot product with TF seems to pay off: https://relinklabs.com/tensorflow-vs-numpy
        M = self.tf.matmul(row_factor, self.tf.transpose(col_factor))
        return self.sess.run(M)

    def fit(self, X, y):
        print("Computing M: (%i × %i)" % (self.nb_users, self.nb_works))
        indices, values, self.means = self.make_matrix(X, y)

        self.chrono.save('fill and center matrix')

        self.M = self.factorize(indices, values)

        self.chrono.save('factor matrix')

    def predict(self, X):
        return self.M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)] + self.means[X[:, 0].astype(np.int64)]

    def get_shortname(self):
        return 'wals'
