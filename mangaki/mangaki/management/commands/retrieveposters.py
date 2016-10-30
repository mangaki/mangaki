from django.core.management.base import BaseCommand
from mangaki.models import Work
import requests

class Command(BaseCommand):
    help = 'Downloads posters'
    def add_arguments(self, parser):
        parser.add_argument('work_id', nargs='*', type=int)
        parser.add_argument('--check-exists', action='store_true')
        parser.add_argument('--ratelimit', type=int, default=10)

    def handle(self, *args, **options):
        qs = Work.objects.exclude(ext_poster='')
        if options['work_id']:
            qs = qs.filter(pk__in=options['work_id'])

        nb_success = 0
        failed = []
        recent = []
        with requests.Session() as s:  # We use a session to use connection pooling
            num_remaining = len(qs)
            for work in qs:
                if not (num_remaining % 10):
                    self.stdout.write('Remaining: {:d}'.format(num_remaining))
                num_remaining -= 1
                if work.int_poster:
                    if not options['check_exists']:
                        continue
                    try:
                        with work.int_poster.open() as f:
                            pass
                    except FileNotFoundError:
                        pass
                    else:
                        continue

                while len(recent) >= options['ratelimit']:
                    now = time.time()
                    recent = [t for t in recent if now - t < 1.]
                    if len(recent) >= options['ratelimit']:
                        time.sleep(min(max(1.1 - now + recent[0], 0.), 1.))
                    else:
                        recent.append(now)

                if work.retrieve_poster(session=s):
                    nb_success += 1
                else:
                    failed.append(work)

        if nb_success:
            self.stdout.write(self.style.SUCCESS(
                '{:d} posters sucessfully downloaded.'.format(nb_success)))
        if failed:
            self.stdout.write(self.style.ERROR('Some posters failed to download:'))
            for work in failed:
                self.stdout.write(self.style.ERROR(
                    ' - {:s} ({:s})'.format(work.title, work.ext_poster)))
