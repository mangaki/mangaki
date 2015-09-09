from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from mangaki.models import Neighborship, Rating
from collections import Counter


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        values = {'like': 2, 'dislike': -2, 'neutral': 0.1, 'willsee': 0.5, 'wontsee': -0.5}
        for user in User.objects.all():
            print(user.id, user.username)
            c = 0
            neighbors = Counter()
            for my in Rating.objects.filter(user=user):
                for her in Rating.objects.filter(work=my.work):
                    c += 1
                    neighbors[her.user.id] += values[my.choice] * values[her.choice]
            print(c, 'operations performed')
            for user_id in neighbors:
                Neighborship.objects.update_or_create(user=user, neighbor=User.objects.get(id=user_id), defaults={'score': neighbors[user_id]})
