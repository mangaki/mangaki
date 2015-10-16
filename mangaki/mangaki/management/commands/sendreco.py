from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.template import Context
from django.template.loader import get_template
from django.db.models import Count
from django.db import connection
from mangaki.models import Rating, Recommendation, Work
from collections import Counter
import numpy as np
import json
import sys

def Base64Decode(loaded):
    dtype = np.dtype(loaded[0])
    arr = np.frombuffer(base64.decodestring(loaded[1]),dtype)
    if len(loaded) > 2:
        return arr.reshape(loaded[2])
    return arr

class Command(BaseCommand):
    args = ''
    help = 'Sends recommendations to users'
    def handle(self, *args, **options):
        target_user = User.objects.get(username=sys.argv[2])
        KING_ID = target_user.id
        with open('backupSVD.json') as f:
            backup = json.load(f)
            anime_titles = backup['anime_titles']
            anime_ids = backup['anime_ids']
            nb_anime = backup['nb_anime']
        XD = np.load('backupXD.npy')

        seen_titles = set()
        for rating in Rating.objects.filter(user__id=KING_ID).select_related('work'):
            if rating.choice != 'willsee':
                seen_titles.add(rating.work.title)

        ranking = sorted((XD[KING_ID, j], anime_ids[j]) for j in range(1, nb_anime + 1) if str(j) in anime_titles)[::-1]

        # Summarize the results of the ranking for KING_ID:
        # “=> rank, title, score”
        svd = User.objects.get(username='svd')
        c = 0
        for i, (rating, work_id) in enumerate(ranking, start=1):
            title = anime_titles[str(work_id)]
            if title not in seen_titles:
                print('=>', i, title, rating)
                if Recommendation.objects.filter(user=svd, target_user=target_user, work__id=work_id).count() == 0:
                    Recommendation(user=svd, target_user=target_user, work=Work.objects.get(id=work_id)).save()
                c += 1
            elif i < 10:
                print(i, title, rating)
            if c >= 10:
                break
