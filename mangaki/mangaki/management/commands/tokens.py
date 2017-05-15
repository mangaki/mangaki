from django.core.management.base import BaseCommand
from django.conf import settings
import hashlib


class Command(BaseCommand):
    args = ''
    help = 'Generate tokens from HASH_NACL'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs=1, type=str)

    def handle(self, *args, **options):
        username = options.get('username')[0]
        message = settings.HASH_NACL + username
        self.stdout.write(self.style.SUCCESS(hashlib.sha1(message.encode('utf-8')).hexdigest()))
