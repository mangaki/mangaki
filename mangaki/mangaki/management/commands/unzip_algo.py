from django.core.management.base import BaseCommand

from zero import get_algo_backup


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
                algo.save(algo.get_backup_filename())
            self.stdout.write(self.style.SUCCESS('Successfully unzipped %s (%.1f MB)' % (algo_name, algo.size)))
        else:
            self.stdout.write(self.style.WARNING('Pickle of %s is already unzipped' % algo_name))
