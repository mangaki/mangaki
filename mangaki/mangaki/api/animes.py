from rest_framework import serializers, viewsets
from mangaki.models import Anime
from .works import work_fields, WorkSerializer
from .genres import GenreSerializer
from .editors import EditorSerializer
from .search import WorkSearchFilter

class AnimeSerializer(WorkSerializer):
    editor = EditorSerializer(read_only=True)
    genres = GenreSerializer(read_only=True, many=True, source='genre')

    class Meta:
        model = Anime
        fields = work_fields + ('editor', 'genres', 'nb_episodes', 'origin', 'anidb_aid')

class AnimeViewSet(viewsets.ModelViewSet):
    queryset = Anime.objects.select_related('category', 'editor').prefetch_related('genre', 'artists').order_by('work_ptr_id')
    serializer_class = AnimeSerializer
    filter_backends = (WorkSearchFilter,)
