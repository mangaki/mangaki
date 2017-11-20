from mangaki.algo import RecommendationAlgorithm, register_algorithm
from sklearn.ensemble import GradientBoostingRegressor as GBR
from mangaki.algo.als import MangakiALS
from mangaki.algo.dataset import Dataset
from django.conf import settings
import json
import numpy as np
import os.path
import logging


@register_algorithm('gbr')
class MangakiGBR(RecommendationAlgorithm):
    def __init__(self, nb_components=20, nb_estimators=2):
        super().__init__()
        self.nb_components = nb_components
        self.nb_estimators = nb_estimators
        self.T = None

    def load(self, filename):
        backup = super().load(filename)
        # What should be saved for this model? Depends on gbr.get_params

    def prepare_features(self, X, U, V):
        X_full = []
        for (user_id, work_id) in X:
            features = np.concatenate((U[user_id],
                                       V[work_id],
                                       #  self.T[work_id], #  Possible but 98s
                                       U[user_id] * V[work_id]))
            X_full.append(features)
        return np.array(X_full)

    def fit(self, X, y):
        if self.T is None:
            self.load_tags()

        self.als = MangakiALS(self.nb_components)
        try:
            self.als.load(self.als.get_backup_filename())
        except:
            self.als.set_parameters(self.nb_users, self.nb_works)
            self.als.fit(X, y)
            self.als.compute_all_errors(X, y, X, y)

        self.chrono.save('fit ALS model')

        X_full = self.prepare_features(X, self.als.U, self.als.VT.T)

        self.chrono.save('build features')

        self.gbr = GBR(n_estimators=self.nb_estimators)
        self.gbr.fit(X_full, y)
        logging.debug('feature_importances=%s', str(self.gbr.feature_importances_))
        logging.debug('train_score=%s', str(self.gbr.train_score_))

        self.chrono.save('fit GBR model')

    def predict(self, X):
        X_full = self.prepare_features(X, self.als.U, self.als.VT.T)
        return self.gbr.predict(X_full)

    def get_shortname(self):
        return 'gbr-%d' % self.nb_components
