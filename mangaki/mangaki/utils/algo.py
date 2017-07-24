from mangaki.utils.wals import MangakiWALS
from mangaki.utils.als import MangakiALS
from mangaki.utils.knn import MangakiKNN
from mangaki.utils.svd import MangakiSVD
from mangaki.utils.gbr import MangakiGBR
from mangaki.utils.data import Dataset


ALGOS = {
    'knn': lambda: MangakiKNN(),
    'svd': lambda: MangakiSVD(20),
    'als': lambda: MangakiALS(20),
    'wals': lambda: MangakiWALS(20),
    'gbr' : lambda: MangakiGBR(20),
}


def fit_algo(algo_name, triplets, titles=None, categories=None):
    algo = ALGOS[algo_name]()
    dataset = Dataset()

    if titles is not None:
        dataset.titles = dict(titles)
    if categories is not None:
        dataset.categories = dict(categories)
    anonymized = dataset.make_anonymous_data(triplets)
    algo.set_parameters(anonymized.nb_users, anonymized.nb_works)
    if algo_name == 'gbr':
        algo.load_dataset(dataset)
    algo.fit(anonymized.X, anonymized.y)
    if algo_name in {'svd', 'als', 'knn', 'gbr'}:
        algo.save(algo.get_backup_filename())
        dataset.save('ratings-' + algo.get_backup_filename())
    return dataset, algo

def get_algo_backup(algo_name):
    algo = ALGOS[algo_name]()
    algo.load(algo.get_backup_filename())
    return algo

def get_dataset_backup(algo_name):
    algo = ALGOS[algo_name]()
    dataset = Dataset()
    dataset.load('ratings-' + algo.get_backup_filename())
    return dataset