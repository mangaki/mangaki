from sklearn.utils.extmath import randomized_svd
from scipy.spatial.distance import pdist, squareform
from scipy.sparse import csc_matrix
from numpy.random import choice
from mangaki.utils.values import rating_values
from mangaki.models import Rating
import pandas
import numpy as np


def diameter(r, points):
    nb_points = points.shape[0]
    return ((2 / (nb_points * (nb_points - 1)) *
            ((pdist(points)**r).sum()))**(1 / r))


def diameter_0(points):
    r = 1
    premier = diameter(r, points)
    deuxième = diameter(r / 2, points)
    while premier - deuxième > 0.01 * deuxième:
        premier = diameter(r, points)
        r = r / 2
        deuxième = diameter(r, points)
    return deuxième


class BuildMatrix(object):

    def build_matrix(self, fname=None):
        user_list, item_list, data = [], [], []

        if fname is None:
            content = Rating.objects.values_list('user_id',
                                                 'work_id',
                                                 'rating')
            for user_id, item_id, rating in content:
                user_list.append(user_id)
                item_list.append(item_id)
                data.append(rating_values[rating])
        else:
            content = pandas.read_csv(fname,
                                      header=None).as_matrix()
            for user_id, item_id, rating in content:
                user_list.append(user_id)
                item_list.append(item_id)
                data.append(rating_values[rating])

        user_set = set(user_list)
        item_set = set(item_list)
        user_dict = {v: k for k, v in enumerate(user_set)}
        item_dict = {v: k for k, v in enumerate(item_set)}
        row = [user_dict[v] for v in user_list]
        col = [item_dict[v] for v in item_list]
        matrix = csc_matrix((data, (row, col)), shape=(
            len(user_set), len(item_set)))
        self.item_set = item_set
        self.user_set = user_set
        self.item_dict = item_dict
        self.user_dict = user_dict
        return matrix


class SimilarityMatrix(object):

    def __init__(self, matrix, nb_components_svd=10,
                 fname=None, algo='svd', metric='cosine'):
        self.nb_components_svd = nb_components_svd
        self.algo = algo
        self.matrix = matrix
        self.similarity_matrix = self.make_similarity_matrix(metric)

    def make_svd_matrix(self):
        self.U, self.sigma, self.VT = randomized_svd(
            self.matrix, self.nb_components_svd)

    def make_similarity_matrix(self, metric):
        if self.algo == 'svd':
            self.make_svd_matrix()
            return 1 - squareform(pdist(self.VT.T, metric=metric))
        return 1 - squareform(pdist(self.matrix.T, metric=metric))


class MangakiUniform(object):

    def __init__(self, items):
        self.items = items

    def sample_k(self, nb_points):
        return choice(self.items, nb_points).tolist()


class MangakiDPP(object):

    def __init__(self, items, similarity_matrix):
        self.items = items
        self.similarity_matrix = similarity_matrix

    def sample_k(self, *args, **kwargs):
        MAX_ITER = 10
        for i in range(MAX_ITER):
            try:
                return self._sample_k(*args, **kwargs)
            except np.linalg.linalg.LinAlgError as e:
                print('LinAlgError in MangakiDPP')
        raise ValueError('Too much LinAlgError')

    def _sample_k(self, k, max_nb_iterations=1000, rng=np.random):
        """
        Thanks to mehdidc on github : https://github.com/mehdidc/dpp
        Sample a list of k items from a DPP defined
        by the similarity matrix L. The algorithm
        is iterative and runs for max_nb_iterations.
        The algorithm used is from
        (Fast Determinantal Point Process Sampling withw
        Application to Clustering, Byungkon Kang, NIPS 2013)
        """
        items = self.items
        L = self.similarity_matrix
        initial = rng.choice(range(len(items)), size=k, replace=False)
        X = [False] * len(items)
        for i in initial:
            X[i] = True
        X = np.array(X)
        for i in range(max_nb_iterations):
            u = rng.choice(np.arange(len(items))[X])
            v = rng.choice(np.arange(len(items))[~X])
            Y = X.copy()
            Y[u] = False
            L_Y = L[Y, :]
            L_Y = L_Y[:, Y]
            L_Y_inv = np.linalg.inv(L_Y)
            c_v = L[v:v + 1, :]
            c_v = c_v[:, v:v + 1]
            b_v = L[Y, :]
            b_v = b_v[:, v:v + 1]
            c_u = L[u:u + 1, :]
            c_u = c_u[:, u:u + 1]
            b_u = L[Y, :]
            b_u = b_u[:, u:u + 1]
            p = min(1, c_v - np.dot(np.dot(b_v.T, L_Y_inv), b_v) /
                    (c_u - np.dot(np.dot(b_u.T, L_Y_inv.T), b_u)))
            if rng.uniform() <= p:
                X = Y[:]
                X[v] = True
        return np.array(items)[X]


def compare(similarity, algos, nb_points, nb_iterations=20):

    resultats = np.zeros([len(algos), 2])

    for _ in range(nb_iterations):
        for i in range(len(algos)):
            items = algos[i].sample_k(nb_points)
            points = similarity.matrix[:, items].T.toarray()

            det = np.linalg.det(squareform(pdist(
                points,
                metric='cosine')))

            diam = diameter_0(points)

            resultats[i, 0] += det
            resultats[i, 1] += diam
    resultats /= nb_iterations

    return resultats


if __name__ == '__main__':
    build_matrix = BuildMatrix()
    matrix = build_matrix.build_matrix(fname='/home/voisin/Bureau/ratings.csv')
    similarity = SimilarityMatrix(matrix, nb_components_svd=70)
    items = list(build_matrix.item_dict.values())
    uniform = MangakiUniform(items)
    dpp = MangakiDPP(items, similarity.similarity_matrix)
    algos = [uniform, dpp]
    results = compare(similarity, algos, 20)
