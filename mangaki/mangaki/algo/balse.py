from .recommendation_algorithm import RecommendationAlgorithm, register_algorithm
from .als import MangakiALS
from .lasso import MangakiLASSO


@register_algorithm('balse')
class MangakiBALSE(RecommendationAlgorithm):
    M = None
    U = None
    VT = None

    def __init__(self,
                 nb_components=10,
                 nb_iterations=10,
                 lambda_=0.1,
                 alpha=0.01,
                 with_bias=True,
                 gamma=5,
                 T=None):
        super().__init__()
        self.nb_components = nb_components
        self.nb_iterations = nb_iterations
        self.lambda_ = lambda_
        self.alpha = alpha
        self.with_bias = with_bias
        self.gamma = gamma
        self.T = T
        self.nb_tags = None

        self.als = MangakiALS(self.nb_components, self.nb_iterations, self.lambda_)
        self.lasso = MangakiLASSO(self.with_bias, self.alpha)

    def fit(self, X, y):
        self.als.set_parameters(self.nb_users, self.nb_works)
        self.lasso.set_parameters(self.nb_users, self.nb_works)
        self.lasso.nb_tags = self.nb_tags
        self.lasso.T = self.T

        self.als.fit(X, y)
        self.lasso.fit(X, y)

    def predict(self, X):
        y_als = self.als.predict(X)
        y_lasso = self.lasso.predict(X)
        y_pred = []
        for i, (user_id, work_id) in enumerate(X):
            if self.lasso.nb_rated[work_id] < self.gamma:
                y_pred.append(y_lasso[i])
            else:
                y_pred.append(y_als[i])
        return y_pred

    def get_shortname(self):
        return 'balse:(%s)|(%s)' % (self.als.get_shortname(), self.lasso.get_shortname())
