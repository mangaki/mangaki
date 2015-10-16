from django.contrib.auth.models import User
from mangaki.models import Rating
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

def run():
    start = datetime.now()
    KING_ID = User.objects.get(username='jj').id
    anime_titles = {}
    anime_ids = set()
    rs = Rating.objects.all().select_related('work')
    cp0 = datetime.now()
    print(cp0 - start)
    for i, rating in enumerate(rs, start=1):
        if i % 10000 == 0:
            print(i)
        if rating.work.id not in anime_ids:
            anime_ids.add(rating.work.id)
            anime_titles[rating.work.id] = rating.work.title
    cp1 = datetime.now()
    print(cp1 - cp0)
    seen_titles = set()
    for rating in Rating.objects.filter(user__id=KING_ID).select_related('work'):
        if rating.choice != 'willsee':
            seen_titles.add(rating.work.title)
    cp2 = datetime.now()
    print(cp2 - cp1)
    nb_users = max(user.id for user in User.objects.all())
    nb_anime = len(anime_ids)
    anime_ids = list(anime_ids)
    inversed = {anime_ids[i]: i for i in range(nb_anime)}
    print("Computing X: (%i×%i)" % (nb_users, nb_anime))
    cp3 = datetime.now()
    print(cp3 - cp2)
    print(nb_users, '×', nb_anime)
    values = {'favorite': 10, 'like': 2, 'dislike': -2, 'neutral': 0.1, 'willsee': 0.5, 'wontsee': -0.5}
    X = lil_matrix((nb_users + 1, nb_anime + 1))
    for rating in Rating.objects.select_related('work', 'user'):
        if rating.work.id < nb_anime:
            X[rating.user.id, inversed[rating.work.id]] = values[rating.choice]

    # Ranking computation
    cp4 = datetime.now()
    print(cp4 - cp3)
    U, sigma, VT = randomized_svd(X, NB_COMPONENTS, n_iter=3, random_state=42)
    print('Formes', U.shape, sigma.shape, VT.shape)
    print(sigma)
    print('mon vecteur (taille %d)' % len(U[KING_ID]), U[KING_ID])
    """for i, line in enumerate(VT):
        print('=> Ligne %d' % i, '(ma note : %f)' % U[KING_ID][i])
        sorted_line = sorted((line[j], anime_titles[anime_ids[j]]) for j in range(1, nb_anime + 1) if j in anime_titles)[::-1]
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
                f.write(json.dumps({'v': [v / math.sqrt(x_norm[k]) if x_norm[k] != 0 else float('inf') for k, v in enumerate(vi)]}))"""
    XD = np.dot(np.dot(U, np.diag(sigma)), VT)
    print('Forme de XD', XD.shape)

    np.save('backupXD', XD)

    backup = {'anime_titles': anime_titles, 'anime_ids': anime_ids, 'nb_anime': nb_anime}

    with open('backupSVD.json', 'w') as f:
        f.write(json.dumps(backup))

    return

    ranking = sorted((XD[KING_ID, j], anime_titles[anime_ids[j]]) for j in range(1, nb_anime + 1) if j in anime_titles)[::-1]

    # Summarize the results of the ranking for KING_ID:
    # “=> rank, title, score”
    c = 0
    for i, (rating, title) in enumerate(ranking, start=1):
        if title not in seen_titles:
            print('=>', i, title, rating)
            c += 1
        elif i < 10:
            print(i, title, rating)
        if c >= 10:
            break
    print(len(connection.queries))
    for line in connection.queries:
        print(line)
    end = datetime.now()
    print(end - start)
