from django.core.management.base import BaseCommand
from django.conf import settings
from mangaki.views import compute_token
from django.contrib.auth import get_user_model
from django.db import connection


class Command(BaseCommand):
    args = ''
    help = 'Generate tokens from HASH_NACL'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs=1, type=str)

    def handle(self, *args, **options):
        username = options.get('username')[0]
        if username == '*':
            with open('mails.txt', 'w') as f:
                for user in get_user_model().objects.filter(profile__newsletter_ok=True):
                    if user.email:
                        f.write('%d;%s;%s;%s\n' % (user.id, user.username, user.email, compute_token(user.username)))
        else:
            self.stdout.write(self.style.SUCCESS(compute_token(username)))
