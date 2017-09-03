from mangaki.utils.wals import MangakiWALS
from mangaki.utils.als import MangakiALS
from mangaki.utils.knn import MangakiKNN
from mangaki.utils.svd import MangakiSVD
from django.core.management.base import BaseCommand

from mangaki.models import Rating, Work
from mangaki.algo import fit_algo


class Command(BaseCommand):
    args = ''
    help = 'Train a recommendation algorithm'

    def add_arguments(self, parser):
        parser.add_argument('algo_name', type=str)
        parser.add_argument('--csv', dest='output_csv', action='store_true', default=False)

    def handle(self, *args, **options):
        algo_name = options.get('algo_name')
        output_csv = options.get('output_csv')
        triplets = Rating.objects.values_list('user_id', 'work_id', 'choice')
        titles = None
        categories = None
        if output_csv:
            meta_triplets = Work.objects.values_list('id', 'title', 'category')
            titles = {work_id: title for work_id, title, _ in meta_triplets}
            categories = {work_id: cat_id for work_id, _, cat_id in meta_triplets}

        fit_algo(algo_name, triplets, titles=titles, categories=categories, output_csv=output_csv)
        self.stdout.write(self.style.SUCCESS('Successfully fit %s' % algo_name))
