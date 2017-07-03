import os

from django.core.management.base import BaseCommand
import csv
import tarfile

from mangaki import settings
from mangaki.models import Work


class Command(BaseCommand):
    help = 'Extract / Load a dump of posters as an archive format'

    def add_arguments(self, parser):
        parser.add_argument('--filename')
        parser.add_argument('--archive-filename')
        parser.add_argument('--load', action='store_true')
        parser.add_argument('--create-archive', action='store_true')

    def handle(self, *args, **options):
        filename = options['filename']
        load_mode = options['load']
        should_create_archive = options['create_archive']
        target_path = os.path.join(settings.MEDIA_ROOT, 'posters')

        if not load_mode:
            self.stdout.write('Dumping posters.')
            relevant_works = Work.objects.exclude(int_poster='').iterator()

            with open(filename, 'w') as f:
                writer = csv.writer(f)
                for work in relevant_works:
                    writer.writerow([work.title, work.int_poster])

            self.stdout.write(self.style.SUCCESS('CSV written.'))

            if should_create_archive:
                self.stdout.write('Creating the archive of posters.')
                archive_filename = options['archive_filename']
                with tarfile.open(archive_filename, 'w:gz') as f:
                    f.add(target_path)

                self.stdout.write(self.style.SUCCESS('Archive written.'))
        else:
            self.stdout.write('Loading posters from dump.')
            self.stdout.write(self.style.WARNING('WARNING: archive should be uncompress prior to this.'))
            titles = []
            posters = {}
            with open(filename, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    title, poster_link = row
                    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, poster_link)):
                        self.stdout.write(
                            self.style.ERROR('Failed to access to {}\'s poster, did you uncompress the archive?'
                                             .format(title)))
                        continue

                    titles.append(title)
                    posters[title] = poster_link

            works = Work.objects.filter(title__in=titles).all()
            for work in works:
                if work.int_poster != posters[work.title]:
                    work.int_poster = posters[work.title]
                    work.save()

                    self.stdout.write(self.style.SUCCESS('Poster of {} updated.'.format(work.title)))

            self.stdout.write(self.style.SUCCESS('Posters were fully loaded!'))
