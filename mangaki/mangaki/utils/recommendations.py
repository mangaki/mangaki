import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix

from mangaki.models import Rating, Work
from mangaki.utils.fit_algo import fit_algo, get_algo_backup
from mangaki.utils.chrono import Chrono
from mangaki.utils.ratings import current_user_ratings
from mangaki.utils.values import rating_values

NB_RECO = 10
CHRONO_ENABLED = True


def user_exists_in_backup(user, algo_name):
    try:
        algo = get_algo_backup(algo_name)
        return user.id in algo.dataset.encode_user
    except FileNotFoundError:
        return False


def get_pos_of_best_works_for_user_via_algo(algo, user_id, work_ids, limit=None):
    if algo.get_shortname().startswith("knn"):
        encoded_user_id = algo.nb_users
    else:
        encoded_user_id = algo.dataset.encode_user[user_id]
    encoded_works = algo.dataset.encode_works(work_ids)
    X_test = np.asarray([[encoded_user_id, encoded_work_id] for encoded_work_id in encoded_works])
    y_pred = algo.predict(X_test)
    pos_of_best = y_pred.argsort()[::-1]  # Get top work indices in decreasing value
    if limit is not None:
        pos_of_best = pos_of_best[:limit]  # Up to some limit
    return pos_of_best

def get_reco_algo(request, algo_name='knn', category='all'):
    chrono = Chrono(is_enabled=CHRONO_ENABLED)
    already_rated_works = list(current_user_ratings(request))
    if request.user.is_anonymous:
        assert request.user.id is None
        # We only support KNN for anonymous users, since the offline models did
        # not learn anything about them.
        # FIXME: We should also force KNN for new users for which we have no
        # offline trained model available.
        algo_name = 'knn'

    chrono.save('get rated works')

    try:
        algo = get_algo_backup(algo_name)
    except FileNotFoundError:
        triplets = list(
            Rating.objects.values_list('user_id', 'work_id', 'choice'))
        chrono.save('get all %d interesting ratings' % len(triplets))
        algo = fit_algo(algo_name, triplets)

    if algo_name == 'knn':
        available_works = set(algo.dataset.encode_work.keys())
        framed_rated_works = (pd.DataFrame(list(current_user_ratings(request).items()), columns=['work_id', 'choice'])
                              .query('work_id in @available_works'))
        framed_rated_works['encoded_work_id'] = algo.dataset.encode_works(framed_rated_works['work_id'])
        framed_rated_works['rating'] = framed_rated_works['choice'].map(rating_values)
        nb_rated_works = len(framed_rated_works)
        ratings_from_user = coo_matrix((framed_rated_works['rating'],([0.] * nb_rated_works, framed_rated_works['encoded_work_id'])), shape=(1, algo.nb_works))
        ratings_from_user = ratings_from_user.tocsr()

        #Expands knn.M with current user ratings (vstack is too slow)
        algo.M.data = np.hstack((algo.M.data, ratings_from_user.data))
        algo.M.indices = np.hstack((algo.M.indices, ratings_from_user.indices))
        algo.M.indptr = np.hstack((algo.M.indptr, (ratings_from_user.indptr + algo.M.nnz)[1:]))
        algo.M._shape = (algo.M.shape[0] + ratings_from_user.shape[0], ratings_from_user.shape[1])

        chrono.save('loading knn and expanding with current user ratings')

    chrono.save('fit %s' % algo.get_shortname())

    if category != 'all':
        category_filter = set(Work.objects.filter(category__slug=category).values_list('id', flat=True))
    else:
        category_filter = algo.dataset.interesting_works

    filtered_works = list((algo.dataset.interesting_works & category_filter) - set(already_rated_works))
    chrono.save('remove already rated, left {:d}'.format(len(filtered_works)))

    pos_of_best = get_pos_of_best_works_for_user_via_algo(algo, request.user.id, filtered_works, limit=NB_RECO)
    best_work_ids = [filtered_works[pos] for pos in pos_of_best]

    chrono.save('compute every prediction')

    works = Work.objects.in_bulk(best_work_ids)
    # Some of the works may have been deleted since the algo backup was created.
    ranked_work_ids = [work_id for work_id in best_work_ids if work_id in works]

    chrono.save('get bulk')

    return {'work_ids': ranked_work_ids, 'works': works}
