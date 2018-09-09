from django.core.management.base import BaseCommand

from mangaki.utils.fit_algo import get_algo_backup
from django.conf import settings


class Command(BaseCommand):
    args = ''
    help = 'Unzip a recommendation algorithm pickle'

    def add_arguments(self, parser):
        parser.add_argument('algo_name', type=str)

    def handle(self, *args, **options):
        algo_name = options.get('algo_name')
        algo = get_algo_backup(algo_name)
        if algo.M is None:
            algo.unzip()
            if algo.is_serializable:
                algo.save(settings.ML_SNAPSHOT_ROOT)
            self.stdout.write(self.style.SUCCESS('Successfully unzipped %s (%.1f MB)' % (algo_name, algo.size / 1e6)))
        else:
            self.stdout.write(self.style.WARNING('Pickle of %s is already unzipped' % algo_name))
