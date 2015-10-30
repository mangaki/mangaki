from django.contrib.auth.models import User
from mangaki.models import Rating, Work
from scipy.sparse import lil_matrix
from sklearn.utils.extmath import randomized_svd
import numpy as np
from django.db import connection
from datetime import datetime
import base64
import json
import math

NB_COMPONENTS = 10

def array_to_json_serializable(ndarray):
    return [str(ndarray.dtype),base64.b64encode(ndarray),ndarray.shape]

def Base64Decode(jsonDump):
    loaded = json.loads(jsonDump)
    dtype = np.dtype(loaded[0])
    arr = np.frombuffer(base64.decodestring(loaded[1]),dtype)
    if len(loaded) > 2:
        return arr.reshape(loaded[2])
    return arr

class Chrono(object):
    checkpoint = datetime.now()
    def save(self, title):
        now = datetime.now()
        print(title, now - self.checkpoint)
        self.checkpoint = now

def run():
    KING_ID = User.objects.get(username='jj').id
    chrono = Chrono()

    anime_titles = {}
    anime_ids = list(Rating.objects.values_list('work_id', flat=True).distinct())
    for work in Work.objects.values('id', 'title'):
        anime_titles[work['id']] = work['title']
    print(len(anime_ids))

    chrono.save('get_work_ids')

    seen_works = set(Rating.objects.filter(user__id=KING_ID).exclude(choice='willsee').values_list('work_id', flat=True))

    chrono.save('get_seen_works')

    nb_users = max(user.id for user in User.objects.all())
    nb_anime = len(anime_ids)
    inversed = {anime_ids[i]: i for i in range(nb_anime)}
    print("Computing X: (%i×%i)" % (nb_users, nb_anime))
    print(nb_users, '×', nb_anime)
    values = {'favorite': 10, 'like': 2, 'dislike': -2, 'neutral': 0.1, 'willsee': 0.5, 'wontsee': -0.5}
    X = lil_matrix((nb_users + 1, nb_anime))
    i = 0
    for user_id, work_id, choice in Rating.objects.values_list('user_id', 'work_id', 'choice'):#select_related('work', 'user'):
        X[user_id, inversed[work_id]] = values[choice]
    np.save('backupX', X)

    chrono.save('fill matrix')

    # Ranking computation
    U, sigma, VT = randomized_svd(X, NB_COMPONENTS, n_iter=3, random_state=42)
    print('Formes', U.shape, sigma.shape, VT.shape)

    chrono.save('factor matrix')

    print(sigma)
    print('mon vecteur (taille %d)' % len(U[KING_ID]), U[KING_ID])
    for i, line in enumerate(VT):
        print('=> Ligne %d' % (i + 1), '(ma note : %f)' % U[KING_ID][i])
        sorted_line = sorted((line[j], anime_titles[anime_ids[j]]) for j in range(nb_anime))[::-1]
        top5 = sorted_line[:10]
        bottom5 = sorted_line[-10:]
        for anime in top5:
            print(anime)
        for anime in bottom5:
            print(anime)
        if i == 0 or i == 1:  # First two vectors explaining variance
            with open('vector%d.json' % (i + 1), 'w') as f:
                vi = X.dot(line).tolist()
                x_norm = [np.dot(X.data[k], X.data[k]) / (nb_anime + 1) for k in range(nb_users + 1)]
                f.write(json.dumps({'v': [v / math.sqrt(x_norm[k]) if x_norm[k] != 0 else float('inf') for k, v in enumerate(vi)]}))
    XD = np.dot(np.dot(U, np.diag(sigma)), VT)
    print('Forme de XD', XD.shape)
    # print(VT.dot(VT.transpose()))

    chrono.save('compute product of components')

    np.save('backupXD', XD)

    backup = {'anime_titles': anime_titles, 'anime_ids': anime_ids, 'nb_anime': nb_anime}

    with open('backupSVD.json', 'w') as f:
        f.write(json.dumps(backup))

    # return

    ranking = sorted((XD[KING_ID, j], anime_ids[j], anime_titles[anime_ids[j]]) for j in range(nb_anime))[::-1]

    # Summarize the results of the ranking for KING_ID:
    # “=> rank, title, score”
    c = 0
    for i, (rating, work_id, title) in enumerate(ranking, start=1):
        if work_id not in seen_works:
            print('=>', i, title, rating)
            c += 1
        elif i < 20:
            print(i, title, rating)
        if c >= 20:
            break

    print(len(connection.queries), 'queries')
    for line in connection.queries:
        print(line)

    chrono.save('complete')
