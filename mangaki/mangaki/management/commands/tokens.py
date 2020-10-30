from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from mangaki.utils.tokens import compute_token
from django.contrib.auth import get_user_model
from django.db import connection
from django.conf import settings
import yaml
from jinja2 import Template


class Command(BaseCommand):
    args = ''
    help = 'Generate tokens for a certain salt'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='+', type=str)
        parser.add_argument('--salt', type=str, required=True)
        parser.add_argument('--email-template', type=str)

    def handle(self, *args, **options):
        usernames = options['username']
        salt = options['salt']

        if options['email_template'] is None:
            for username in usernames:
                self.stdout.write(self.style.SUCCESS(
                    '{} {}'.format(username, compute_token(salt, username))))

        else:
            filename = options['email_template']
            with open(filename, 'r') as f:
                newsletter = yaml.safe_load(f)
            message = Template(newsletter['body'])

            queryset = get_user_model().objects.filter(profile__newsletter_ok=True)
            if '*' not in usernames:
                queryset = queryset.filter(username__in=usernames)

            nb_mails = queryset.count()
            self.stdout.write('Sending {:d} mails'.format(nb_mails))
            for rank, user in enumerate(queryset, start=1):
                if user.email:
                    token = compute_token(salt, user.username)
                    if input('OK? {:s} '.format(user.username)) == 'y':
                        ok = send_mail(
                            newsletter['subject'],
                            message.render(username=user.username, token=token),
                            newsletter['from'], [user.email], fail_silently=False)
                        prefix = '[{} / {}]'.format(rank, nb_mails)
                        if ok:
                            self.stdout.write(self.style.SUCCESS('{}: {} OK'.format(prefix, user.username)))
                        else:
                            self.stdout.write(self.style.ERROR('{}: {} NOK'.format(prefix, user.username)))
