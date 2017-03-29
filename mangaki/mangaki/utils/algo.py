from mangaki.utils.wals import MangakiWALS
from mangaki.utils.als import MangakiALS
from mangaki.utils.knn import MangakiKNN
from mangaki.utils.svd import MangakiSVD
from mangaki.utils.data import Dataset


ALGOS = {
    'knn': lambda: MangakiKNN(),
    'svd': lambda: MangakiSVD(20),
    'als': lambda: MangakiALS(20),
    'wals': lambda: MangakiWALS(20),
}


def fit_algo(algo_name, triplets, backup_filename):
    algo = ALGOS[algo_name]()
    dataset = Dataset()

    anonymized = dataset.make_anonymous_data(triplets)
    algo.set_parameters(anonymized.nb_users, anonymized.nb_works)
    algo.fit(anonymized.X, anonymized.y)
    if algo_name in {'svd', 'als'}:  # KNN is constantly refreshed
        algo.save(backup_filename)
        dataset.save('ratings-' + backup_filename)
    return dataset, algo
