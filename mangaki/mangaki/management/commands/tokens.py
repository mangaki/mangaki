from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from mangaki.utils.tokens import compute_token
from django.contrib.auth import get_user_model
from django.db import connection
from django.conf import settings
import os
import yaml
from jinja2 import Template


DEBUG_USERNAMES = ['jj', 'RaitoBezarius']


class Command(BaseCommand):
    args = ''
    help = 'Generate tokens for a certain salt'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs=1, type=str)
        parser.add_argument('salt', nargs=1, type=str)

    def handle(self, *args, **options):
        username = options.get('username')[0]
        salt = options.get('salt')[0]
        newsletter = yaml.load(open(os.path.join(settings.DATA_DIR, 'newsletter.yaml')).read())
        message = Template(newsletter['body'])

        if username not in ['DEBUG', '*']:
            self.stdout.write(self.style.SUCCESS(compute_token(salt, username)))
            return

        if username == 'DEBUG':
            queryset = get_user_model().objects.filter(profile__newsletter_ok=True, username__in=DEBUG_USERNAMES)
        else:
            queryset = get_user_model().objects.filter(profile__newsletter_ok=True)[:5]
        nb_mails = queryset.count()
        for rank, user in enumerate(queryset, start=1):
            if user.email:
                token = compute_token(salt, user.username)
                ok = send_mail(
                    newsletter['subject'],
                    message.render(username=user.username, token=token),
                    newsletter['from'], [user.email], fail_silently=False)
                prefix = '[{} / {}]'.format(rank, nb_mails)
                if ok:
                    self.stdout.write(self.style.SUCCESS('{}: {} OK'.format(prefix, user.username)))
                else:
                    self.stdout.write(self.style.ERROR('{}: {} NOK'.format(prefix, user.username)))
