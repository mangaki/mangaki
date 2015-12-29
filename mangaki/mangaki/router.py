from rest_framework import routers, viewsets
from mangaki import models
from mangaki import serializers

router = routers.DefaultRouter()

# Work related

class EditorViewSet(viewsets.ModelViewSet):
    queryset = models.Editor.objects.all()
    serializer_class = serializers.EditorSerializer

class StudioViewSet(viewsets.ModelViewSet):
    queryset = models.Studio.objects.all()
    serializer_class = serializers.StudioSerializer

class GenreViewSet(viewsets.ModelViewSet):
    queryset = models.Genre.objects.all()
    serializer_class = serializers.GenreSerializer

class TrackViewSet(viewsets.ModelViewSet):
    queryset = models.Track.objects.all()
    serializer_class = serializers.TrackSerializer

class ArtistViewSet(viewsets.ModelViewSet):
    queryset = models.Artist.objects.all()
    serializer_class = serializers.ArtistSerializer

class AnimeViewSet(viewsets.ModelViewSet):
    queryset = models.Anime.objects.all()
    serializer_class = serializers.AnimeSerializer

class MangaViewSet(viewsets.ModelViewSet):
    queryset = models.Manga.objects.all()
    serializer_class = serializers.MangaSerializer

class OSTViewSet(viewsets.ModelViewSet):
    queryset = models.OST.objects.all()
    serializer_class = serializers.OSTSerializer

class RatingViewSet(viewsets.ModelViewSet):
    queryset = models.Rating.objects.all()
    serializer_class = serializers.RatingSerializer

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = models.Profile.objects.all()
    serializer_class = serializers.ProfileSerializer

class SuggestionViewSet(viewsets.ModelViewSet):
    queryset = models.Suggestion.objects.all()
    serializer_class = serializers.SuggestionSerializer

router.register(r'editor', EditorViewSet)
router.register(r'studio', StudioViewSet)
router.register(r'genre', GenreViewSet)
router.register(r'track', TrackViewSet)
router.register(r'artist', ArtistViewSet)
router.register(r'anime', AnimeViewSet)
router.register(r'manga', MangaViewSet)
router.register(r'ost', OSTViewSet)
router.register(r'rating', RatingViewSet)
router.register(r'profile', ProfileViewSet)
router.register(r'suggestion', SuggestionViewSet)
