from rest_framework import serializers, viewsets
from mangaki.models import Anime
from .works import work_fields, WorkSerializer
from .search import WorkSearchFilter

class AnimeSerializer(serializers.HyperlinkedModelSerializer):
    director = serializers.StringRelatedField(read_only=True)
    composer = serializers.StringRelatedField(read_only=True)
    studio = serializers.StringRelatedField(read_only=True)
    author = serializers.StringRelatedField(read_only=True)
    editor = serializers.StringRelatedField(read_only=True)
    genre = serializers.StringRelatedField(read_only=True, many=True)

    class Meta:
        model = Anime
        fields = '__all__'

class AnimeViewSet(viewsets.ModelViewSet):
    queryset = Anime.objects.select_related('director', 'composer', 'studio', 'author', 'editor').prefetch_related('genre').order_by('work_ptr_id')
    serializer_class = AnimeSerializer
    filter_backends = (WorkSearchFilter,)
