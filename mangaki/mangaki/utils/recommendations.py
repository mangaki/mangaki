from collections import Counter
from mangaki.models import Rating, ColdStartRating, Work
from mangaki.utils.chrono import Chrono
from mangaki.utils.data import Dataset
from django.contrib.auth.models import User
from django.db.models import Count
from mangaki.utils.algo import ALGOS, fit_algo
from mangaki.utils.ratings import current_user_ratings
import numpy as np
import json
import os.path


NB_RECO = 10
CHRONO_ENABLED = True


def get_reco_algo(request, algo_name='knn', category='all'):
    chrono = Chrono(is_enabled=CHRONO_ENABLED)
    already_rated_works = list(current_user_ratings(request))
    if request.user.is_anonymous:
        current_user_id = 0
        # We only support KNN for anonymous users, since the offline models did
        # not learn anything about them.
        # FIXME: We should also force KNN for new users for which we have no
        # offline trained model available.
        algo_name = 'knn'
    else:
        current_user_id = request.user.id

    chrono.save('get rated works')

    if algo_name == 'knn':
        queryset = Rating.objects.filter(work__in=already_rated_works)
        dataset = Dataset()
        triplets = list(
            queryset.values_list('user_id', 'work_id', 'choice'))
        if request.user.is_anonymous:
            triplets.extend([
                (current_user_id, work_id, choice)
                for work_id, choice in current_user_ratings(request).items()
            ])

        anonymized = dataset.make_anonymous_data(triplets)

        chrono.save('make first anonymous data')

        algo = ALGOS['knn']()
        algo.set_parameters(anonymized.nb_users, anonymized.nb_works)
        algo.fit(anonymized.X, anonymized.y)

        chrono.save('prepare first fit')

        encoded_neighbors = algo.get_neighbors([dataset.encode_user[current_user_id]])
        neighbors = dataset.decode_users(encoded_neighbors[0])  # We only want for the first user

        chrono.save('get neighbors')

        # Only keep useful ratings for recommendation
        triplets = list(
            Rating.objects
                  .filter(user__id__in=neighbors + [current_user_id])
                  .exclude(choice__in=['willsee', 'wontsee'])
                  .values_list('user_id', 'work_id', 'choice')
        )
        if request.user.is_anonymous:
            triplets.extend([
                (current_user_id, work_id, choice)
                for work_id, choice in current_user_ratings(request).items()
                if choice not in ('willsee', 'wontsee')
            ])
    else:
        # Every rating is useful
        triplets = list(
            Rating.objects.values_list('user_id', 'work_id', 'choice'))

    chrono.save('get all %d interesting ratings' % len(triplets))

    dataset = Dataset()
    algo = ALGOS[algo_name]()
    if algo.has_backup():
        algo.load(algo.get_backup_filename())
        dataset.load('ratings-' + algo.get_backup_filename())
    else:
        dataset, algo = fit_algo(algo_name, triplets, algo.get_backup_filename())

    chrono.save('fit %s' % algo.get_shortname())

    if category != 'all':
        category_filter = set(Work.objects.filter(category__slug=category).values_list('id', flat=True))
    else:
        category_filter = dataset.interesting_works

    filtered_works = (dataset.interesting_works & category_filter) - set(already_rated_works)
    encoded_works = dataset.encode_works(filtered_works)
    nb_test = len(encoded_works)

    chrono.save('remove already rated')

    encoded_request_user_id = dataset.encode_user[current_user_id]
    X_test = np.asarray([[encoded_request_user_id, encoded_work_id] for encoded_work_id in encoded_works])
    y_pred = algo.predict(X_test)
    pos = y_pred.argsort()[-NB_RECO:][::-1]  # Get top NB_RECO work indices in decreasing value

    chrono.save('compute every prediction')

    best_work_ids = [dataset.decode_work[encoded_work_id] for _, encoded_work_id in X_test[pos]]
    works = Work.objects.in_bulk(best_work_ids)

    chrono.save('get bulk')

    return {'work_ids': best_work_ids, 'works': works}
