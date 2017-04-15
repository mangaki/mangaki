from mangaki.utils import dpplib
from mangaki.utils.algo import get_algo_backup, get_dataset_backup
from random import sample
import numpy as np


class MangakiUniform:
    def __init__(self, items):
        self.items = items

    def sample_k(self, nb_points):
        return sample(self.items, nb_points)


class MangakiDPP:
    def __init__(self, work_ids=None, vectors=None):
        self.work_ids = np.array(work_ids)
        self.set_vectors(vectors)

    def set_vectors(self, vectors):
        self.vectors = vectors

    def compute_similarity(self):
        print('compute')
        self.L = self.vectors.dot(self.vectors.T)
        print('finish compute')

    def load_from_algo(self, algo_name):
        algo = get_algo_backup(algo_name)
        dataset = get_dataset_backup(algo_name)
        available_work_ids = list(set(self.work_ids) & set(dataset.encode_work.keys()))
        self.work_ids = np.array(available_work_ids)
        self.set_vectors(algo.VT.T[dataset.encode_works(available_work_ids)])
        self.compute_similarity()
        self.preprocess()

    def preprocess(self, indices=None):
        print('preprocess')
        if indices is None:
            indices = list(range(len(self.vectors)))
        D, V = np.linalg.eig(self.L[np.ix_(indices, indices)])
        self.D = np.real(D)
        self.V = np.real(V)
        print('finish preprocess')

    def sample_k(self, k):
        sampled_indices = [int(index) for index in dpplib.sample_k(k, self.D, self.V)]
        return self.work_ids[sampled_indices]
