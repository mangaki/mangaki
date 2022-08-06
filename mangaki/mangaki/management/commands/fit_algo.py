# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from django.core.management.base import BaseCommand

from mangaki.models import Rating, Work
from mangaki.utils.fit_algo import fit_algo, get_algo_backup, dump_2d_embeddings


class Command(BaseCommand):
    args = ''
    help = 'Train a recommendation algorithm'

    def add_arguments(self, parser):
        parser.add_argument('algo_name', type=str)
        parser.add_argument('--csv', dest='output_csv', action='store_true', default=False)
        parser.add_argument('--viz_only', dest='viz_only', action='store_true', default=False)

    def handle(self, *args, **options):
        algo_name = options.get('algo_name')
        output_csv = options.get('output_csv')
        viz_only = options.get('viz_only')

        triplets = Rating.objects.values_list('user_id', 'work_id', 'choice')
        titles = None
        categories = None
        if output_csv:
            meta_triplets = Work.objects.values_list('id', 'title', 'category')
            titles = {work_id: title for work_id, title, _ in meta_triplets}
            categories = {work_id: cat_id for work_id, _, cat_id in meta_triplets}

        if not viz_only:
            algo = fit_algo(algo_name, triplets, titles=titles, categories=categories, output_csv=output_csv)
            self.stdout.write(self.style.SUCCESS('Successfully fit %s (%.1f MB)' % (algo_name, algo.size / 1e6)))
        else:
            algo = get_algo_backup(algo_name)
            dump_2d_embeddings(algo, f'points-{algo_name}.json')
            self.stdout.write(self.style.SUCCESS('Successfully update viz %s' % (algo_name)))
