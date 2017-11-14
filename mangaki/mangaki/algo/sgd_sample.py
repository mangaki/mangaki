import numpy as np
from sklearn.metrics import mean_squared_error


class MangakiSGD:
    def __init__(self, nb_users, nb_works, nb_components=20, nb_iterations=10,
                 gamma=0.01, lambda_=0.1):
        self.nb_components = nb_components
        self.nb_iterations = nb_iterations
        self.nb_users = nb_users
        self.nb_works = nb_works
        self.gamma = gamma
        self.lambda_ = lambda_
        # self.bias = np.random.random()
        # self.bias_u = np.random.random(self.nb_users)
        # self.bias_v = np.random.random(self.nb_works)
        self.U = np.random.random((self.nb_users, self.nb_components))
        self.V = np.random.random((self.nb_works, self.nb_components))

    def fit(self, X, y):
        for epoch in range(self.nb_iterations):
            step = 0
            for (i, j), rating in zip(X, y):
                if step % 100000 == 0:  # Pour afficher l'erreur de train
                    y_pred = self.predict(X)
                    print('Train RMSE (epoch={}, step={}): %f'.format(
                        epoch, step, mean_squared_error(y, y_pred) ** 0.5))
                predicted_rating = self.predict_one(i, j)
                error = predicted_rating - rating
                # self.bias += self.gamma * error
                # self.bias_u[i] -= self.gamma * (error +
                #                                 self.lambda_ * self.bias_u[i])
                # self.bias_v[j] -= self.gamma * (error +
                #                                 self.lambda_ * self.bias_v[j])
                self.U[i] -= self.gamma * (error * self.V[j] +
                                           self.lambda_ * self.U[i])
                self.V[j] -= self.gamma * (error * self.U[i] +
                                           self.lambda_ * self.V[j])
                step += 1

    def predict_one(self, i, j):
        return (  # self.bias + self.bias_u[i] + self.bias_v[j] +
                self.U[i].dot(self.V[j]))

    def predict(self, X):
        y = []
        for i, j in X:
            y.append(self.predict_one(i, j))
        return np.array(y)
