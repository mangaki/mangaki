from rest_framework import serializers, viewsets
from mangaki.models import Editor

class EditorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Editor
        fields = ('title')

class EditorViewSet(viewsets.ModelViewSet):
    queryset = Editor.objects.all()
    serializer_class = EditorSerializer
