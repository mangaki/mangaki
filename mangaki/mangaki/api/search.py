from rest_framework import filters
from django.db.models import Func, F, Value

class WorkSearchFilter(filters.BaseFilterBackend):
    """
    Filter the works using trigrams in the DB.
    """

    def filter_queryset(self, request, queryset, view):
        search_text = request.GET.get('search', None)
        if search_text is not None:
            return queryset.\
                    annotate(sim_score=Func(F('title'), Value(search_text), function='SIMILARITY')).\
                    filter(sim_score__gte=Func(function='SHOW_LIMIT')).\
                    order_by('-sim_score')
        else:
            return queryset
