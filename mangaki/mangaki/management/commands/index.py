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
