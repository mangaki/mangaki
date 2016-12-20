from django.core.management.base import BaseCommand, CommandError
from mangaki.models import Work, Rating
from django.db import connection
from django.db.models import Count
from collections import Counter


class Command(BaseCommand):
    args = ''
    help = 'Lookup some work'

    def add_arguments(self, parser):
        parser.add_argument('query', nargs=1, type=str)

    def handle(self, *args, **options):
        query = options.get('query')[0]
        work = Work.objects.filter(title__icontains=query).annotate(Count('rating')).order_by('-rating__count')[0]
        print(work.title, work.id)
        nb = Counter()
        for rating in Rating.objects.filter(work=work):
            nb[rating.choice] += 1
        print(nb)
