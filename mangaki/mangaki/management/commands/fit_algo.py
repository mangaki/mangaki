from django.core.management.base import BaseCommand
from mangaki.utils.algo import fit_algo
from mangaki.models import Rating


class Command(BaseCommand):
    args = ''
    help = 'Train a recommendation algorithm'

    def add_arguments(self, parser):
        parser.add_argument('algo_name', type=str)

    def handle(self, *args, **options):
        algo_name = options.get('algo_name')
        backup_filename = '%s.pickle' % algo_name
        triplets = Rating.objects.values_list('user_id', 'work_id', 'choice')
        fit_algo(algo_name, triplets, backup_filename)
        self.stdout.write(self.style.SUCCESS('Successfully fit %s' % algo_name))
