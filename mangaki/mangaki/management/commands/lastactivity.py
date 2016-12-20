from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
import datetime


class Command(BaseCommand):
    args = ''
    help = 'Displays last activity'

    def handle(self, *args, **options):
        for user, date in User.objects.order_by('-last_login').values_list('username', 'last_login')[:5]:
            print(user, datetime.datetime.strftime(date, '%d/%m/%Y %H:%M:%S'))
