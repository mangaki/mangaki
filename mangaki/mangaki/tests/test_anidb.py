import os

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.models import Category, Editor, Studio, Work, Role, Staff, Artist
from mangaki.utils.anidb import AniDB


class AniDBTest(TestCase):
    @staticmethod
    def create_anime(**kwargs):
        anime = Category.objects.get(slug='anime')
        return Work.objects.create(category=anime, **kwargs)

    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_DATA_DIR, filename), 'r', encoding='utf-8') as f:
            return f.read()

    def setUp(self):
        # FIXME: The defaults for editor and studio in Work requires those to
        # exist, or else foreign key constraints fail.
        Editor.objects.create(pk=1)
        # Studio.objects.create(pk=1)
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
        anime = self.anidb.get_or_update_work(11606)

        self.assertEqual(anime.title, 'Sangatsu no Lion')
        self.assertEqual(anime.nb_episodes, 22)
        self.assertEqual(anime.studio.title, 'Shaft')

        author_ids = [q.artist_id for q in Staff.objects.filter(work_id=anime.pk, role_id=3)]
        author_names = [Artist.objects.get(pk=at_id).name for at_id in author_ids]
        self.assertEqual(author_names, ['Umino Chika'])

        composer_ids = [q.artist_id for q in Staff.objects.filter(work_id=anime.pk, role_id=4)]
        composer_names = [Artist.objects.get(pk=cp_id).name for cp_id in composer_ids]
        self.assertEqual(composer_names, ['Hashimoto Yukari'])

        director_ids = [q.artist_id for q in Staff.objects.filter(work_id=anime.pk, role_id=5)]
        director_names = [Artist.objects.get(pk=dt_id).name for dt_id in director_ids]
        self.assertEqual(director_names, ['Shinbou Akiyuki', 'Okada Kenjirou'])
