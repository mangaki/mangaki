from rest_framework import serializers, viewsets
from mangaki.models import Work

work_fields = (
    'title',
    'source',
    'poster',
    'nsfw',
    'date',
    'synopsis',
    'category'
)

class WorkSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Work
        fields = work_fields

class WorkViewSet(viewsets.ModelViewSet):
    queryset = Work.objects.all()
    serializer_class = WorkSerializer
