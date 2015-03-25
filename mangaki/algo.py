from django.contrib.auth.models import User
from mangaki.models import Anime, Rating
from scipy.sparse import lil_matrix
from sklearn.utils.extmath import randomized_svd
import numpy as np

NB_COMPONENTS = 15

def run():
    KING_ID = User.objects.get(username='Sedeto').id
    anime_titles = {}
    anime_ids = set()
    for rating in Rating.objects.all():
        if rating.work.id not in anime_ids:
            anime_ids.add(rating.work.id)
            anime_titles[rating.work.id] = rating.work.title
    seen_titles = set()
    for rating in Rating.objects.filter(user__id=KING_ID):
        seen_titles.add(rating.work.title)
    nb_users = max(user.id for user in User.objects.all())
    nb_anime = len(anime_ids)
    anime_ids = list(anime_ids)
    inversed = {anime_ids[i]: i for i in range(nb_anime)}
    print(nb_users, '×', nb_anime)
    values = {'like': 2, 'dislike': -2, 'neutral': 0.1, 'willsee': 0.5, 'wontsee': -0.5}
    X = lil_matrix((nb_users + 1, nb_anime + 1))
    for rating in Rating.objects.all():
        if rating.work.id < nb_anime:
            X[rating.user.id, inversed[rating.work.id]] = values[rating.choice]
    U, sigma, VT = randomized_svd(X, NB_COMPONENTS, n_iter=3, random_state=42)
    XD = np.dot(np.dot(U, np.diag(sigma)), VT)
    ranking = sorted((XD[KING_ID, j], anime_titles[anime_ids[j]]) for j in range(1, nb_anime + 1) if j in anime_titles)[::-1]
    c = 0
    for i, (rating, title) in enumerate(ranking):
        if title not in seen_titles:
            print('=>', i + 1, title, rating)
            c += 1
        elif i < 10:
            print(i + 1, title, rating)
        if c >= 10:
            break
