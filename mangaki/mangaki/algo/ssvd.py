from mangaki.algo.recommendation_algorithm import RecommendationAlgorithm, register_algorithm
from surprise import SVD, Dataset, Reader
import pandas as pd
import numpy as np


@register_algorithm('ssvd')
class MangakiSSVD(RecommendationAlgorithm):
    def __init__(self, rank=10, nb_iterations=20):
        super().__init__()
        self.model = SVD(n_factors=rank, n_epochs=nb_iterations)

    def fit(self, X, y):
        self.reader = Reader(rating_scale=(y.min(), y.max()))
        data = Dataset.load_from_df(pd.DataFrame(np.column_stack((X, y))), self.reader)
        train = data.build_full_trainset()
        self.chrono.save('prepare data')
        self.model.fit(train)
        self.chrono.save('fit')

    def predict(self, X):
        y = np.repeat(0, len(X))
        data = Dataset.load_from_df(pd.DataFrame(np.column_stack((X, y))), self.reader)
        train = data.build_full_trainset()
        test = train.build_testset()
        pred = self.model.test(test)
        return np.array([rating.est for rating in pred])

    def get_shortname(self):
        return 'ssvd'
