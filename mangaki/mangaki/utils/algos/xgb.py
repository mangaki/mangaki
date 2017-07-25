import logging

import numpy as np
from xgboost.sklearn import XGBRegressor

import pickle

from .als import MangakiALS
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
        self.als = None
        self.nb_iterations = nb_iterations

    def load(self, filename):
        self.model = pickle.loads(filename)

    def save(self, filename):
        pickle.dumps(self.model, filename)

    def build_features(self, X, y):
        als = MangakiALS(20, LAMBDA=-0.1)
        als.set_parameters(self.nb_users, self.nb_works)
        if self.verbose:
            logger.info('Fitting ALS.')
        als.fit(X, y)

        self.als = als

        return self.build_features_through_als(X)

    def build_features_through_als(self, X):
        return np.array([
            # Note we pass a *tuple* here.
            np.concatenate((
                # self.als.U[user_id] * self.als.VT.T[work_id],
                self.als.U[user_id],
                self.als.VT.T[work_id]
            )) for user_id, work_id in X
        ])

    def fit(self, X, y):
        if self.verbose:
            # len(y) lines.
            # 40 columns: The ALS used has 20 components, so 2 * 20.
            logger.info("Computing the feature `matrix` ({} × {}) through ALS vectors."
                        .format(len(y), 2*20))

        matrix = self.build_features(X, y)

        if self.verbose:
            logger.info('Shape of `matrix` is: {}'.format(matrix.shape))

        self.chrono.save('fit ALS and build features matrix')

        self.model.fit(
            matrix,
            y,
            verbose=self.verbose
        )

        self.chrono.save('fit and boost trees')

    def predict(self, X):
        if not self.als:
            raise ValueError('ALS has not been fitted! Cannot build the features!')

        return self.model.predict(self.build_features_through_als(X))

    def get_shortname(self):
        params = self.model.get_params()

        return 'xgb-{}-{}-{}-{}'.format(
            params['n_estimators'],
            params['max_depth'],
            params['objective'],
            params['booster']
        )
