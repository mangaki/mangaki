from rest_framework import serializers, viewsets
from mangaki.models import Work, Staff
from .artists import ArtistSerializer

work_fields = (
    'url',
    'title',
    'source',
    'poster',
    'nsfw',
    'date',
    'staff',
    'synopsis',
    'category'
)

class StaffSerializerInWork(serializers.HyperlinkedModelSerializer):
    artist = ArtistSerializer(read_only=True)
    role = serializers.StringRelatedField(read_only=True) # FIXME: Make it more clean, not using __str__ method.
    class Meta:
        model = Staff
        fields = ('artist', 'role')

class WorkSerializer(serializers.HyperlinkedModelSerializer):
    category = serializers.StringRelatedField(read_only=True)
    staff = StaffSerializerInWork(read_only=True, many=True, source='staff_set')
    class Meta:
        model = Work
        fields = work_fields

class WorkViewSet(viewsets.ModelViewSet):
    queryset = Work.objects.all()
    serializer_class = WorkSerializer
