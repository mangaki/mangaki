from django.core.management.base import BaseCommand, CommandError
from mangaki.models import Work, Rating
from django.db import connection
from django.db.models import Count
from collections import Counter
import random
import sys

class Command(BaseCommand):
    args = ''
    help = 'Print ranking and make decks'

    def handle(self, *args, **options):
        for work in Work.objects.all():
            work.update_ratings()
