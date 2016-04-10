from rest_framework import filters

class WorkSearchFilter(filters.BaseFilterBackend):
    """
    Filter the works using trigrams in the DB.
    """

    def filter_queryset(self, request, queryset, view):
        search_text = request.GET.get('search', None)
        if search_text is not None:
            return queryset.search(search_text)
        else:
            return queryset
