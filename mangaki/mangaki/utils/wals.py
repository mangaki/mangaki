from collections import defaultdict, Counter
from mangaki.utils.chrono import Chrono
import numpy as np
import pickle

import tensorflow as tf
from tensorflow.contrib.factorization.python.ops import factorization_ops
from tensorflow.python.framework import sparse_tensor

sess = tf.InteractiveSession()

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

class MangakiWALS(object):
    M = None
    U = None
    VT = None
    def __init__(self, NB_COMPONENTS=20):
        """An implementation of the Weighted Alternate Least Squares.
        NB_COMPONENTS: the number of components in the factorization"""
        self.NB_COMPONENTS = NB_COMPONENTS
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

    def set_parameters(self, nb_users, nb_works):
        self.nb_users = nb_users
        self.nb_works = nb_works

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
        rows = self.nb_users
        cols = self.nb_works
        dims = self.NB_COMPONENTS
        row_wts = 0.1 + np.random.rand(rows)
        col_wts = 0.1 + np.random.rand(cols)
        inp = sparse_tensor.SparseTensor(indices, values, [rows, cols])
        use_factors_weights_cache = True
        model = factorization_ops.WALSModel(
            rows,
            cols,
            dims,
            unobserved_weight=1,#.1,
            regularization=0.001,#001,
            row_weights=None,#row_wts,
            col_weights=None,#col_wts,
            use_factors_weights_cache=use_factors_weights_cache)
        simple_train(model, inp, 25)
        row_factor = model.row_factors[0].eval()
        print('Shape', row_factor.shape)
        col_factor = model.col_factors[0].eval()
        print('Shape', col_factor.shape)
        out = np.dot(row_factor, np.transpose(col_factor))
        return out

    def fit(self, X, y):
        print("Computing M: (%i × %i)" % (self.nb_users, self.nb_works))
        indices, values, self.means = self.make_matrix(X, y)

        self.chrono.save('fill and center matrix')

        self.M = self.factorize(indices, values)
        
        self.chrono.save('factor matrix')

    def predict(self, X):
        return self.M[X[:, 0].astype(np.int64), X[:, 1].astype(np.int64)] + self.means[X[:, 0].astype(np.int64)]

    def __str__(self):
        return '[WALS]'

    def get_shortname(self):
        return 'wals'
