from rest_framework import serializers, viewsets
from mangaki.models import Genre

class GenreSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='api:genre-detail')
    class Meta:
        model = Genre
        fields = ('url', 'title')

class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
