from django.core.management.base import BaseCommand, CommandError
from mangaki.models import Work, Rating
from django.db import connection
from django.db.models import Count
from collections import Counter
import sys


class Command(BaseCommand):
    args = ''
    help = 'Lookup some work'

    def handle(self, *args, **options):
        work = Work.objects.filter(title__icontains=args[0]).annotate(Count('rating')).order_by('-rating__count')[0]
        print(work.title, work.id)
        nb = Counter()
        for rating in Rating.objects.filter(work=work):
            nb[rating.choice] += 1
        print(nb)
