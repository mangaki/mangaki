from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import Count

from mangaki.models import Rating, Work


class Command(BaseCommand):
    args = ''
    help = 'Lookup some work'

    def add_arguments(self, parser):
        parser.add_argument('query', nargs=1, type=str)

    def handle(self, *args, **options):
        query = options.get('query')[0]
        work = Work.objects.filter(title__icontains=query).annotate(Count('rating')).order_by('-rating__count')[0]
        self.stdout.write(self.style.SUCCESS('%s (ID: %d)' % (work.title, work.id)))
        nb = Counter()
        for rating in Rating.objects.filter(work=work):
            nb[rating.choice] += 1
        self.stdout.write(str(nb))
