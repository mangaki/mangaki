from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.template import Context
from django.template.loader import get_template
from django.db.models import Count
from django.db import connection
from mangaki.models import Rating, Recommendation, Work
from mangaki.utils.svd import MangakiSVD
from mangaki.utils.values import rating_values
from collections import Counter
import numpy as np
import json
import sys

class Command(BaseCommand):
    args = ''
    help = 'Sends recommendations to users'
    def handle(self, *args, **options):
        username = sys.argv[2]

        X = []
        y = []

        for user_id, work_id, choice in Rating.objects.values_list('user_id', 'work_id', 'choice'):
            X.append((user_id, work_id))
            y.append(rating_values[choice])

        svd = MangakiSVD()
        # svd.fit(X, y)
        svd.load('backup.pickle')
        svd.get_reco(username, sending=True)
