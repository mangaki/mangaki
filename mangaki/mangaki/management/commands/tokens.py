from django.core.management.base import BaseCommand
from django.conf import settings
from mangaki.utils.tokens import compute_token
from django.contrib.auth import get_user_model
from django.db import connection


class Command(BaseCommand):
    args = ''
    help = 'Generate tokens for a certain salt'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs=1, type=str)
        parser.add_argument('salt', nargs=1, type=str)

    def handle(self, *args, **options):
        username = options.get('username')[0]
        salt = options.get('salt')[0]
        if username == '*':
            for user in get_user_model().objects.filter(profile__newsletter_ok=True):
                if user.email:
                    pass  # Send a mail
        else:
            self.stdout.write(self.style.SUCCESS(compute_token(username)))
