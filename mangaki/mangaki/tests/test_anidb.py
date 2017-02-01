from django.test import TestCase
from mangaki.models import Work, Category, Editor, Studio
from mangaki.utils.anidb import AniDB


class AniDBTest(TestCase):

    def create_anime(self, **kwargs):
        anime = Category.objects.get(slug='anime')
        return Work.objects.create(category=anime, **kwargs)

    def setUp(self):
        # FIXME: The defaults for editor and studio in Work requires those to
        # exist, or else foreign key constraints fail.
        Editor.objects.create(pk=1)
        Studio.objects.create(pk=1)
        self.anidb = AniDB('mangakihttp', 1)

    def test_anidb_search(self):
        results = self.anidb.search(q='sangatsu no lion')
        self.assertNotEqual(len(results), 0)

    def test_anidb_get(self):
        anime = self.create_anime(**self.anidb.get(11606))
        self.assertNotEqual(anime.title, '')
