from mangaki.utils.common import RecommendationAlgorithm
from mangaki.utils.data import Dataset


def fit_algo(algo_name, triplets, titles=None, categories=None, output_csv=False):
    algo = RecommendationAlgorithm.instantiate_algorithm(algo_name)
    dataset = Dataset()

    if titles is not None:
        dataset.titles = dict(titles)
    if categories is not None:
        dataset.categories = dict(categories)

    anonymized = dataset.make_anonymous_data(triplets)
    algo.set_parameters(anonymized.nb_users, anonymized.nb_works)
    algo.fit(anonymized.X, anonymized.y)

    if algo.is_serializable:
        algo.save(algo.get_backup_filename())
        dataset.save('ratings-' + algo.get_backup_filename())
        if output_csv:
            dataset.save_csv()
    return dataset, algo

def get_algo_backup(algo_name):
    algo = RecommendationAlgorithm.instantiate_algorithm(algo_name)
    algo.load(algo.get_backup_filename())
    return algo

def get_dataset_backup(algo_name):
    algo = RecommendationAlgorithm.instantiate_algorithm(algo_name)
    dataset = Dataset()
    dataset.load('ratings-' + algo.get_backup_filename())
    return dataset
