from sklearn.utils.extmath import randomized_svd
from scipy.spatial.distance import pdist, squareform
from scipy.sparse import lil_matrix
from numpy.random import choice
from mangaki.utils.values import rating_values
from mangaki.models import Rating
import pandas
import random
import numpy as np

"""
Proposition si on utlise csc_matrix au lieu de lil_matrix
from scipy.sparse import csc_matrix

user_list, item_list, data=[],[], []


if fname is None:
    content = Rating.objects.values_list('user_id',
                                                 'work_id',
                                                 'choice')
    for user_id, item_id, choice in content:
        user_list.append(user_id)
        item_list.append(item_id)
        data.append(rating_values[choice])
else:
    content = pandas.read_csv(fname,
                                      header=None).as_matrix()
    for user_id, item_id, choice in content:
        user_list.append(user_id)
        item_list.append(item_id)
        data.append(rating_values[choice])
        
user_set=set(user_list)
item_set=set(item_list)
user_dict = {v: k for k, v in enumerate(user_set)}
item_dict = {v: k for k, v in enumerate(item_set)}
row=[user_dict[v] for v in user_list]
col=[item_dict[v] for v in item_list]
#data=[rating_values[rating] for rating in Rating.objects.values_list('choice', flat=True)]
matrix = csc_matrix((data, (row, col)), shape=(len(user_set),len(item_set)))
matrix.toarray()
#matrix.toarray()

"""
def build_matrix(self, fname=None):
    user_set, item_set = set(), set()
    if fname is None:
        content = Rating.objects.values_list('user_id',
                                                 'work_id',
                                                 'choice')
        for user_id, item_id in Rating.objects.values_list('user_id',
                                                               'work_id'):
            user_set.add(user_id)
            item_set.add(item_id)
    else:
        content = pandas.read_csv(fname,
                                      header=None).as_matrix()
        for user_id, item_id in content[:, 0:2]:
            user_set.add(user_id)
            item_set.add(item_id)
    user_dict = {v: k for k, v in enumerate(user_set)}
    item_dict = {v: k for k, v in enumerate(item_set)}
    matrix = lil_matrix((len(user_set), len(item_set)), dtype=np.float64)
    for user_id, item_id, rating in content:
        matrix[user_dict[user_id],
                   item_dict[item_id]] = rating_values[rating]
    self.user_dict = user_dict
    self.item_dict = item_dict
    self.user_set = user_set
    self.item_set = item_set
    return matrix













#fonctions permettant de calculer des diamètres
#à appeler ds compare : diameter_0(nb_points, sampled_items) et pareil pr uniform_itemss
#@requires : svd.VT ou alors le changer par matrix ....

def diameter(r, nb_points, items):
    return ((2/(nb_points*(nb_points-1))*((pdist(svd.VT[:, items].T)**r).sum()))**(1/r)) 

def diameter_0(nb_points, items):
    r=1
    premier=diameter(r,10, items)
    deuxième=diameter(r/2,10, items)
    while premier-deuxième >0.01*deuxième :
        premier=diameter(r,10, items)
        r=r/2
        deuxième=diameter(r,10, items)
    return deuxième



class SimilarityMatrix(object):
  
    def __init__(self, fname=None, algo='svd',nb_components_svd , metric='cosine'):
        self.matrix = self.build_matrix(fname)
        self.similarity_matrix = self.make_similarity_matrix('cosine')
        self.nb_components_svd = nb_components_svd
        self.algo=algo

    def make_svd_matrix(self, matrix):
        self.U, self.sigma, self.VT = randomized_svd(matrix, self.nb_components_svd)

    def make_similarity_matrix(self, option):
        if self.algo == 'svd':
            self.matrix=make_svd_matrix(self.matrix)
        return 1 - squareform(pdist(self.matrix.T, metric=option))


class MangakiUniform(object):

    def __init__(self, nb_points):
        self.nb_points = nb_points

    def sample_k(self, items, matrix_similarity):
        uniform_items = items
        random.shuffle(uniform_items)
        return choice(items, self.nb_points).tolist()

    def __str__(self):
        return 'uniform list, nb_points=%d' % self.nb_points


class MangakiDPP(object):

    def __init__(self, similarity):
        self.similarity = similarity

    def sample_k(self, k, max_nb_iterations=1000, rng=np.random):
        """
        Thanks to mehdidc on github : https://github.com/mehdidc/dpp
        Sample a list of k items from a DPP defined
        by the similarity matrix L. The algorithm
        is iterative and runs for max_nb_iterations.
        The algorithm used is from
        (Fast Determinantal Point Process Sampling withw
        Application to Clustering, Byungkon Kang, NIPS 2013)
        """
        self.similarity.build_matrix()
        L = self.similarity.make_similarity_matrix('cosine')
        items = list(self.similarity.user_set)
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
            c_v = L[v:v+1, :]
            c_v = c_v[:, v:v+1]
            b_v = L[Y, :]
            b_v = b_v[:, v:v+1]
            c_u = L[u:u+1, :]
            c_u = c_u[:, u:u+1]
            b_u = L[Y, :]
            b_u = b_u[:, u:u+1]
            p = min(1, c_v - np.dot(np.dot(b_v.T, L_Y_inv), b_v) /
                    (c_u - np.dot(np.dot(b_u.T, L_Y_inv.T), b_u)))
            if rng.uniform() <= p:
                X = Y[:]
                X[v] = True
        return np.array(items)[X]

    def __str__(self):
        return 'sample dpp list, nb_points=%d' % self.nb_points


def compare(nb_points, nb_iterations):
    results_uniform, results_sample_dpp = [], []
    similarity = SimilarityMatrix()
    dpp = MangakiDPP(similarity)
    uniform = MangakiUniform(nb_points)
    indicateur = 0
    pb = 0
    while indicateur != nb_iterations:
        try:
            sampled_items = dpp.sample_k(nb_points)
        except np.linalg.linalg.LinAlgError as err:
            pb = 1
        if pb == 0:
            indicateur = indicateur+1
            uniform_items = uniform.sample_k(list(similarity.user_set),
                                             similarity)
            det_uni = np.linalg.det(squareform(pdist(
                       similarity.matrix[:, uniform_items].T,
                       metric='cosine')))
            det_dpp = np.linalg.det(squareform(pdist(
                       similarity.matrix[:, sampled_items].T,
                       metric='cosine')))
            diam_uni = 2/(nb_points*(nb_points-1))*(pdist(
                         similarity.matrix[:, uniform_items].T).sum())
            diam_dpp = 2/(nb_points*(nb_points-1))*(pdist(
                         similarity.matrix[:, sampled_items].T).sum())
            results_uniform.append([det_uni, diam_uni])
            results_sample_dpp.append([det_dpp, diam_dpp])
        else:
            pb = 0
    print("%s \n %s" % (results_uniform, results_sample_dpp))

#TODO
"""
 Il faudrait que compare prenne une liste d'objets
(MangakiUniform / MangakiDPP / autres si on en créé
plus tard) et les compare entre eux en samplant le
même nombre de points etc
voir mangaki/mangaki/mangaki/management.compare.py

"""
#algos est une liste contenant un objet de MangakiDPP et un de MangakiUniform pr l'instant : dpp le 1er, uniform le 2ème
def compare2(similarity, nb_points, nb_iterations=100, algos):
    
    #results_uniform, results_sample_dpp = [], []
    sum_det_uni, sum_diam_uni, sum_det_dpp, sum_diam_dpp = 0, 0
    indicateur = 0
    pb = 0
    dpp = algos[0]
    uniform = algos[1]

    while indicateur != nb_iterations:
        try:
            sampled_items = dpp.sample_k(nb_points)
        except np.linalg.linalg.LinAlgError as err:
            pb = 1
        if pb == 0:
            indicateur = indicateur+1
            uniform_items = uniform.sample_k(list(similarity.user_set),
                                             similarity)
            det_uni = np.linalg.det(squareform(pdist(
                       similarity.matrix[:, uniform_items].T,
                       metric='cosine')))
            det_dpp = np.linalg.det(squareform(pdist(
                       similarity.matrix[:, sampled_items].T,
                       metric='cosine')))
            diam_uni = diameter_0(nb_points, sampled_items)
            diam_dpp = diameter_0(nb_points, uniform_items)

            sum_det_uni += det_uni
            sum_diam_uni += diam_uni
            sum_det_dpp += det_dpp
            sum_diam_dpp += diam_dpp
            #results_uniform.append([det_uni, diam_uni])
            #results_sample_dpp.append([det_dpp, diam_dpp])
        else:
            pb = 0
    #print("%s \n %s" % (results_uniform, results_sample_dpp)) 
    average_det_uni = sum_det_uni / nb_iterations
    average_diam_uni = sum_diam_uni / nb_iterations
    average_det_dpp = sum_det_dpp / nb_iterations
    average_diam_dpp = sum_diam_dpp / nb_iterations
    return average_det_uni, average_diam_uni, average_det_dpp, average_diam_dpp
