# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from django.conf import settings

from zero.dataset import Dataset
from zero.recommendation_algorithm import RecommendationAlgorithm

from mangaki.utils.viz import dump_2d_embeddings


def fit_algo(algo_name, triplets, titles=None, categories=None,
             output_csv=False):
    algo = RecommendationAlgorithm.instantiate_algorithm(algo_name)
    algo.dataset = Dataset()

    if titles is not None:
        algo.dataset.titles = dict(titles)
    if categories is not None:
        algo.dataset.categories = dict(categories)

    anonymized = algo.dataset.make_anonymous_data(triplets)
    algo.set_parameters(anonymized.nb_users, anonymized.nb_works)
    algo.fit(anonymized.X, anonymized.y)

    if algo.is_serializable:
        algo.save(settings.ML_SNAPSHOT_ROOT)
        if output_csv:
            algo.dataset.save_csv(settings.DATA_ROOT)

    # Save visualization
    if algo_name in {'als', 'svd'}:
        dump_2d_embeddings(algo, f'points-{algo_name}.json')

    return algo


def get_algo_backup(algo_name):
    algo = RecommendationAlgorithm.instantiate_algorithm(algo_name)
    if not algo.is_serializable:
        raise RuntimeError('"{}" is not serializable, cannot load a backup!'
                           .format(algo_name))

    algo.load(settings.ML_SNAPSHOT_ROOT)
    return algo
