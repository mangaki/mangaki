# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from django.core.management.base import BaseCommand
from django.db.models import Count

from mangaki.models import Work
from mangaki.utils.anidb import client


class Command(BaseCommand):
    args = ''
    help = 'Pair with AniDB'

    def handle(self, *args, **options):
        q = (Work.objects.only('pk', 'title', 'ext_poster', 'nsfw')
                         .annotate(rating_count=Count('rating'))
                         .filter(anidb_aid=0, category__slug='anime',
                                 rating_count__gte=6)
                         .order_by('-rating_count'))
        for anime in q:
            print(anime.title, anime.id)
            for proposal in client.search(r'\%s' % anime.title):
                print(proposal)
            anidb_aid = input('Which one? ')
            if anidb_aid == 'q':
                continue
            anime.anidb_aid = int(anidb_aid)
            anime.save()
