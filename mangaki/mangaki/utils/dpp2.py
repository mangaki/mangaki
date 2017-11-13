from random import sample

import numpy as np

from mangaki.utils import dpplib
from mangaki.algo import get_algo_backup, get_dataset_backup


def get_volume(vectors):
    return np.linalg.det(vectors.dot(vectors.T))


class MangakiUniform:
    def __init__(self, vectors=None, REPEAT=10):
        self.vectors = vectors
        self.items = list(range(len(vectors)))

    def sample_k(self, nb_points):
        volumes = []
        for _ in range(self.REPEAT):
            sampled = sample(self.items, nb_points)
            volumes.append((get_volume(self.vectors[sampled]), sampled))
        return max(volumes)[1]


class MangakiDPP:
    def __init__(self, vectors=None, ids=None, REPEAT=5):
        self.REPEAT = REPEAT
        self.vectors = vectors
        self.ids = ids
        self.indices = None if vectors is None else np.array(list(range(len(vectors))))

    def compute_similarity(self, kernel):
        self.L = kernel(self.vectors)

    def load_from_algo(self, algo_name):
        algo = get_algo_backup(algo_name)
        dataset = get_dataset_backup(algo_name)
        available_work_ids = list(set(self.work_ids) & set(dataset.encode_work.keys()))
        self.ids = np.array(available_work_ids)
        self.vectors = algo.VT.T[dataset.encode_works(available_work_ids)]
        self.compute_similarity()
        self.preprocess()

    def preprocess(self):
        D, V = np.linalg.eig(self.L[np.ix_(self.indices, self.indices)])
        self.D = np.real(D)
        self.V = np.real(V)

    def sample_k(self, k):
        volumes = []
        for _ in range(self.REPEAT):
            sampled = [int(index) for index in dpplib.sample_k(k, self.D, self.V)]
            volumes.append((get_volume(self.vectors[sampled]), sampled))
        sampled = max(volumes)[1]
        return self.indices[sampled] if self.ids is None else self.ids[self.indices[sampled]]
