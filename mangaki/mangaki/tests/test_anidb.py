import os

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.models import Category, Editor, Studio, Work
from mangaki.utils.anidb import AniDB


class AniDBTest(TestCase):
    @staticmethod
    def create_anime(**kwargs):
        anime = Category.objects.get(slug='anime')
        return Work.objects.create(category=anime, **kwargs)

    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_FIXTURE_DIR, filename), 'r') as f:
            return f.read()

    def setUp(self):
        # FIXME: The defaults for editor and studio in Work requires those to
        # exist, or else foreign key constraints fail.
        Editor.objects.create(pk=1)
        Studio.objects.create(pk=1)
        self.anidb = AniDB('mangakihttp', 1)
        self.search_fixture = self.read_fixture('search_sangatsu_no_lion.xml')
        self.anime_fixture = self.read_fixture('sangatsu_no_lion.xml')

    @responses.activate
    def test_anidb_search(self):
        responses.add(
            responses.GET,
            AniDB.SEARCH_URL,
            body=self.search_fixture,
            status=200,
            content_type='application/xml'
        )
        anime_query = 'sangatsu no lion'
        results = self.anidb.search(q=anime_query)
        self.assertEqual(len(results), 2)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_anidb_get(self):
        responses.add(
            responses.GET,
            AniDB.BASE_URL,
            body=self.anime_fixture,
            status=200,
            content_type='application/xml'
        )
        anime = self.create_anime(**self.anidb.get_dict(11606))
        self.assertNotEqual(anime.title, '')
