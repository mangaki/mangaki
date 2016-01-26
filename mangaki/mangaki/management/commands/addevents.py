from django.core.management.base import BaseCommand, CommandError
from irl.models import Event

class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        with open('data/events.txt') as f:
            for line in f:
                date, title, place, language = line.strip().split(' ; ')
                Event.objects.update_or_create(date=date, title=title, location=place, defaults={'language': language})