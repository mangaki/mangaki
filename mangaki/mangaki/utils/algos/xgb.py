import logging

import numpy as np
from xgboost.sklearn import XGBRegressor

import pickle

from mangaki.utils.algos.recommendation_algorithm import RecommendationAlgorithm

logger = logging.getLogger(__name__)


class MangakiXGB(RecommendationAlgorithm):
    M = None
    U = None
    VT = None

    def __init__(self,
                 tree_booster: str = 'gbtree',
                 objective: str = 'reg:linear',
                 eta: float = 1.0,
                 n_estimators: int = 100,
                 max_depth: int = 3,
                 nb_iterations: int = 2):
        """
        Initialize a XGBoosted Mangaki algorithm.

        Args:
            tree_booster (str): Tree booster (can be gbtree, gblinear or dart)
            objective (str): objective function, reg:linear or reg:logistic
            eta (float): step size shrinkage
            n_estimators (int): amount of trees to fit
            max_depth (int): maximum depth of a tree
            nb_iterations (int): number of iterations to do boosting
        """
        super().__init__()
        self.model = XGBRegressor(
            max_depth,
            eta,
            n_estimators,
            not self.verbose,  # Silent or not.
            objective,
            tree_booster
        )

        self.nb_iterations = nb_iterations

    def load(self, filename):
        self.model = pickle.loads(filename)

    def save(self, filename):
        pickle.dumps(self.model, filename)

    def make_matrix(self, X, y):
        matrix = np.zeros((self.nb_users, self.nb_works), dtype=np.float16)
        means = np.zeros((self.nb_users,))

        for (user, work), rating in zip(X, y):
            matrix[user][work] = rating

        for i in range(self.nb_users):
            means[i] = np.sum(matrix[i]) / np.sum(matrix[i] != 0)
            if np.isnan(means[i]):
                means[i] = 0
            matrix[i][matrix[i] != 0] -= means[i]

        return matrix

    def fit(self, X, y):
        if self.verbose:
            logger.info("Computing `matrix`: (%i × %i)" % (self.nb_users, self.nb_works))

        matrix = self.make_matrix(X, y)

        self.chrono.save('fill and center matrix')

        X_prescaled = X.copy()
        X_prescaled = (X_prescaled - X.min()) / (X.max() - X.min())
        y_prescaled = y.copy()
        y_prescaled = (y_prescaled - y.min()) / (y.max() - y.min())

        self.model.fit(
            X_prescaled,
            y_prescaled,
            verbose=self.verbose
        )

        self.chrono.save('fit and boost trees')

    def predict(self, X):
        return self.model.predict(X)

    def get_shortname(self):
        params = self.model.get_params()

        return 'xgb-{}-{}-{}-{}'.format(
            params['n_estimators'],
            params['max_depth'],
            params['objective'],
            params['booster']
        )
