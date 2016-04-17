from rest_framework import serializers, viewsets
from mangaki.models import Editor

class EditorSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='api:editor-detail')
    class Meta:
        model = Editor
        fields = ('title', 'url')

class EditorViewSet(viewsets.ModelViewSet):
    queryset = Editor.objects.all()
    serializer_class = EditorSerializer
