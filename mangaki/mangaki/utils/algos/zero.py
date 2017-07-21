from mangaki.utils.algos.recommendation_algorithm import RecommendationAlgorithm


class MangakiZero(RecommendationAlgorithm):
    def __init__(self):
        super().__init__()

    def fit(self, X, y):
        pass

    def predict(self, X):
        return [0] * len(X)

    def get_shortname(self):
        return 'zero'
