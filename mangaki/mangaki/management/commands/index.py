"""
Updating work search index for PostgreSQL full text search.
"""
# SPDX-FileCopyrightText: 2022, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

import logging
from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.postgres.search import SearchVector
# Another day we can use SearchRank and SearchQuery for more sophisticated uses
from django.contrib.postgres.aggregates import StringAgg
from mangaki.models import Work


class Command(BaseCommand):
    """
    https://testdriven.io/blog/django-search/
    https://pganalyze.com/blog/full-text-search-django-postgres
    """
    args = ''
    help = 'Update index, please do this locally'

    def handle(self, *args, **options):
        works = Work.objects.annotate(
            synonyms=StringAgg('worktitle__title', ' / '))
        for work in works:
            work.search_terms = work.synonyms
        Work.objects.bulk_update(works, ['search_terms'], 1000)
        for i, query in enumerate(connection.queries):
            logging.warning('%d %f %s', i, query['time'], query['sql'][:30])

        # Reusing the already existing title_search field does not work
        Work.objects.update(title_search=SearchVector('title', weight='A') +
                            SearchVector('search_terms', weight='B'))
        # Making a new field
        Work.objects.update(titles_search=SearchVector('title', weight='A') +
                            SearchVector('search_terms', weight='B'))

        work = Work.objects.get(id=1)  # Death Note
        print('diff???', work.title_search, work.titles_search)
        # 'death':1 'note':2 vs. 'death':1A 'not':2A
        print('works', Work.objects.filter(title__mangaki_search='death note'))

        # Work.objects.filter(title_search='Death Note'))  # Is empty
        print('works', Work.objects.filter(titles_search='Death Note'))

        # Work.objects.filter(title_search='tower of god'))  # Is empty
        print('works', Work.objects.filter(titles_search='tower of god'))
