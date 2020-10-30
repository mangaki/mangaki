
from django.core.management.base import BaseCommand
from django.db.models import Count

from mangaki.models import Rating, Work, WorkCluster
from mangaki.admin import merge_works


class Command(BaseCommand):
    args = ''
    help = 'Merge workclusters'

    def add_arguments(self, parser):
        parser.add_argument('nb', nargs=1, type=str)

    def handle(self, *args, **options):
        nb_clusters = int(options.get('nb')[0])

        clusters = WorkCluster.objects.order_by('-id').filter(status='unprocessed')
        self.stdout.write('%d WorkClusters' % (clusters.count()))

        c = 0
        for cluster in clusters:
            if cluster.difficulty < 1:
                merge_works(None, WorkCluster.objects.filter(id=cluster.id), force=True)
                c += 1
                self.stdout.write(self.style.SUCCESS('%s was merged' % str(cluster)))
                if c == nb_clusters:
                    break
