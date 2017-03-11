from collections import Counter
from mangaki.models import Rating, ColdStartRating, Work
from mangaki.utils.chrono import Chrono
from mangaki.utils.data import Dataset
from django.contrib.auth.models import User
from django.db.models import Count
from mangaki.utils.algo import ALGOS, fit_algo
import numpy as np
import json
import os.path


NB_RECO = 10
CHRONO_ENABLED = True


def get_reco_algo(user, algo_name='knn', category='all'):
    chrono = Chrono(is_enabled=CHRONO_ENABLED, connection=connection)

    already_rated_works = Rating.objects.filter(user=user).values_list('work_id', flat=True)

    chrono.save('get rated works')

    if algo_name == 'knn':
        queryset = Rating.objects.filter(work__in=already_rated_works)
        dataset = Dataset()
        anonymized = dataset.make_anonymous_data(queryset)

        chrono.save('make first anonymous data')

        algo = ALGOS['knn']()
        algo.set_parameters(anonymized.nb_users, anonymized.nb_works)
        algo.fit(anonymized.X, anonymized.y)

        chrono.save('prepare first fit')

        encoded_neighbors = algo.get_neighbors([dataset.encode_user[user.id]])
        neighbors = dataset.decode_users(encoded_neighbors[0])  # We only want for the first user

        chrono.save('get neighbors')

        # Only keep useful ratings for recommendation
        queryset = Rating.objects.filter(user__id__in=neighbors + [user.id]).exclude(choice__in=['willsee', 'wontsee'])
    else:
        # Every rating is useful
        queryset = Rating.objects.all()

    chrono.save('get all %d interesting ratings' % queryset.count())

    dataset = Dataset()
    backup_filename = '%s.pickle' % algo_name
    if os.path.isfile(os.path.join('pickles', backup_filename)):  # When Algo class will be there: 'if algo.has_backup():'
        algo = ALGOS[algo_name]()
        algo.load(backup_filename)
        dataset.load('ratings-' + backup_filename)
    else:
        dataset, algo = fit_algo(algo_name, queryset, backup_filename)

    chrono.save('fit %s' % algo.get_shortname())

    if category != 'all':
        category_filter = set(Work.objects.filter(category__slug=category).values_list('id', flat=True))
    else:
        category_filter = dataset.interesting_works

    filtered_works = (dataset.interesting_works & category_filter) - set(already_rated_works)
    encoded_works = dataset.encode_works(filtered_works)
    nb_test = len(encoded_works)

    chrono.save('remove already rated')

    encoded_request_user_id = dataset.encode_user[user.id]
    X_test = np.asarray([[encoded_request_user_id, encoded_work_id] for encoded_work_id in encoded_works])
    y_pred = algo.predict(X_test)
    pos = y_pred.argsort()[-NB_RECO:][::-1]  # Get top NB_RECO work indices in decreasing value

    chrono.save('compute every prediction')

    best_work_ids = [dataset.decode_work[encoded_work_id] for _, encoded_work_id in X_test[pos]]
    works = Work.objects.in_bulk(best_work_ids)

    chrono.save('get bulk')

    return {'work_ids': best_work_ids, 'works': works}
