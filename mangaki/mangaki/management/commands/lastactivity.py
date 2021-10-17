import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    args = ''
    help = 'Displays last activity'

    def handle(self, *args, **options):
        for user, date in User.objects.order_by('-last_login').values_list('username', 'last_login')[:10]:
            if date:
                print(user, datetime.datetime.strftime(date, '%d/%m/%Y %H:%M:%S'))
