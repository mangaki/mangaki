import logging
import numpy as np

from mangaki.algo.recommendation_algorithm import RecommendationAlgorithm
from django.test import TestCase


class AlgoTest(TestCase):
    def setUp(self):
        self.nb_users = 5
        self.nb_works = 10
        self.nb_tags = 2
        self.U = np.random.random((self.nb_users, 2))
        self.VT = np.random.random((2, self.nb_works))
        self.T = np.random.random((self.nb_works, self.nb_tags))
        self.M = self.U.dot(self.VT)
        train_user_ids = [1, 2, 3, 3]
        train_work_ids = [0, 1, 0, 1]
        self.X_train = np.column_stack((train_user_ids, train_work_ids))
        self.y_train = self.M[train_user_ids, train_work_ids]
        test_user_ids = [1, 2]
        test_work_ids = [1, 0]
        self.X_test = np.column_stack((test_user_ids, test_work_ids))
        self.y_test = self.M[test_user_ids, test_work_ids]

    def test_fit_predict(self):
        for algo_name in RecommendationAlgorithm.list_available_algorithms():
            algo = RecommendationAlgorithm.instantiate_algorithm(algo_name)
            algo.set_parameters(self.nb_users, self.nb_works)
            if algo_name in {'lasso', 'xals'}:
                algo.nb_tags = self.nb_tags
                algo.T = self.T
            algo.fit(self.X_train, self.y_train)
            y_pred = algo.predict(self.X_test)
            logging.debug('rmse=%.3f algo=%s',
                          algo.compute_rmse(y_pred, self.y_test), algo_name)
