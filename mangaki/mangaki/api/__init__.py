from rest_framework import routers
from .animes import AnimeViewSet
from .categories import CategoryViewSet
from .studios import StudioViewSet
from .editors import EditorViewSet
from .genres import GenreViewSet
from .artists import ArtistViewSet

router = routers.DefaultRouter()
router.register(r'animes', AnimeViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'studios', StudioViewSet)
router.register(r'editors', EditorViewSet)
router.register(r'genres', GenreViewSet)
router.register(r'artists', ArtistViewSet)
