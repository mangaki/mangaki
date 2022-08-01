"""
Updating work search index for PostgreSQL full text search.
"""
# SPDX-FileCopyrightText: 2022, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

import logging
from django.core.management.base import BaseCommand
from mangaki.models import Work
from mangaki.utils.index import reindex


class Command(BaseCommand):
    """
    https://testdriven.io/blog/django-search/
    https://pganalyze.com/blog/full-text-search-django-postgres
    """
    args = ''
    help = """Update Work.search_terms (concatenation of synonyms)
              and Work index, please do this locally"""

    def handle(self, *args, **options):
        reindex()

        '''work = Work.objects.get(id=26931)  # Death Note
                                print('diff???', work.title_search, work.titles_search)
                                # 'death':1 'note':2 vs. 'death':1A 'not':2A
                                print('works', Work.objects.filter(title__mangaki_search='death note'))
                        
                                # Work.objects.filter(title_search='Death Note'))  # Is empty
                                print('works', Work.objects.filter(titles_search='Death Note'))
                                print('test', Work.objects.filter(title__search='Death Note'))
                        
                                # Work.objects.filter(title_search='tower of god'))  # Is empty
                                print('works', Work.objects.filter(titles_search='tower of god').values('id'))
                                print('test', Work.objects.filter(title__search='tower of god'))'''
