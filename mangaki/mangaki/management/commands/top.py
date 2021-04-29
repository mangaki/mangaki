# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from mangaki.choices import TOP_CATEGORY_CHOICES
from mangaki.models import Artist, Ranking, Rating, Top
from mangaki.utils.chrono import Chrono


class Command(BaseCommand):
    args = ''
    help = 'Builds top'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--all', action='store_true', help='Refresh all tops')
        group.add_argument('category', nargs='*', type=str, default='director',
                           choices=['director', 'composer', 'author'],
                           help='Top category to Refresh')

    def handle(self, *args, **options):
        chrono = Chrono(False)

        categories = []
        if options.get('category'):
            categories = set(options.get('category'))
        if options.get('all'):
            categories = {'director', 'composer', 'author'}

        for category in categories:
            self.stdout.write('Refreshing top for {}s'.format(category))

            c = Counter()
            values = {'favorite': 10, 'like': 2, 'neutral': 0.5, 'dislike': -1}
            nb_ratings = Counter()
            nb_stars = Counter()

            for choice, contestant_id in Rating.objects.filter(work__staff__role__slug=category).values_list('choice', 'work__staff__artist'):
                if contestant_id and contestant_id > 1:  # Artiste non inconnu
                    nb_ratings[contestant_id] += 1
                    if choice == 'favorite':
                        nb_stars[contestant_id] += 1
                    c[contestant_id] += values.get(choice, 0)
            chrono.save('enter contestants')

            artist_ids = []
            for artist_id, _ in c.most_common(20):
                artist_ids.append(artist_id)
            artist_by_id = Artist.objects.in_bulk(artist_ids)

            choice = category + 's'
            if choice not in dict(TOP_CATEGORY_CHOICES):
                raise CommandError("Invalid top category '{}'".format(choice))

            top = Top.objects.create(category=choice)
            Ranking.objects.bulk_create([
                Ranking(
                    top=top,
                    content_object=artist_by_id[artist_id],
                    score=score,
                    nb_ratings=nb_ratings[artist_id],
                    nb_stars=nb_stars[artist_id],
                ) for (artist_id, score) in c.most_common(20)
            ])
            chrono.save('get results')

            self.stdout.write(self.style.SUCCESS('Refreshed top for {}s'.format(category)))
