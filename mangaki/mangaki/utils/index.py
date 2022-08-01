import logging
from django.contrib.postgres.aggregates import StringAgg
# Another day we can use SearchRank and SearchQuery for more sophisticated uses
from django.contrib.postgres.search import SearchVector
from django.db import connection
from mangaki.models import Work


def reindex(BATCH_SIZE=1000):
    """
    FYI, the already existing Work.title_search field exists,
    is populated by PostgreSQL using triggers, but cannot be used for search.
    We need to know why before we delete it.
    """

    # Update search_terms (concatenation of synonyms)
    works = Work.objects.annotate(
        synonyms=StringAgg('worktitle__title', ' / '))
    for work in works:
        work.search_terms = work.synonyms
    Work.objects.bulk_update(works, ['search_terms'], BATCH_SIZE)

    for i, query in enumerate(connection.queries):
        logging.warning('%d %f %s', i, query['time'], query['sql'][:30])

    # Update index
    Work.objects.update(titles_search=SearchVector('title', weight='A') +
        SearchVector('search_terms', weight='B'))
    # For doc about weight='A' and 'B', see (#weighting-queries):
    # https://docs.djangoproject.com/fr/4.0/ref/contrib/postgres/search/
