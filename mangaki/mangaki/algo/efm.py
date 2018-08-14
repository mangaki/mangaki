from mangaki.algo.recommendation_algorithm import RecommendationAlgorithm, register_algorithm
from spotlight.interactions import Interactions
from spotlight.factorization.explicit import ExplicitFactorizationModel
import numpy as np


@register_algorithm('efm')
class MangakiEFM(RecommendationAlgorithm):
    def __init__(self, rank=20, nb_iterations=20):
        super().__init__()
        self.model = ExplicitFactorizationModel(n_iter=nb_iterations)

    def fit(self, X, y):
        user_ids = X[:, 0]
        item_ids = X[:, 1]
        ratings = y.astype(np.float32)
        train = Interactions(user_ids=user_ids, item_ids=item_ids, ratings=ratings,
                             num_users=self.nb_users, num_items=self.nb_works)
        self.chrono.save('prepare data')
        self.model.fit(train, verbose=True)
        self.chrono.save('fit')

    def predict(self, X):
        user_ids = X[:, 0].astype(np.int32)
        item_ids = X[:, 1].astype(np.int32)
        print(user_ids.shape)
        print(item_ids.shape)
        return self.model.predict(user_ids, item_ids)

    def get_shortname(self):
        return 'efm'
