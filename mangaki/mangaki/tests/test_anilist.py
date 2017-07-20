from datetime import datetime
from urllib.parse import urljoin
import os

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.wrappers.anilist import to_python_datetime, client, AniList, AniListWorks


class AniListTest(TestCase):
    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_DATA_DIR, filename), 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def add_fake_auth():
        responses.add(
            responses.POST,
            urljoin(AniList.BASE_URL, AniList.AUTH_PATH),
            body='{"access_token":"fake_token","token_type":"Bearer","expires_in":3600,"expires":946684800}',
            status=200,
            content_type='application/json'
        )

    @responses.activate
    def setUp(self):
        self.anilist = AniList('test_client', 'client_secret')
        self.no_anilist = AniList()

    def test_to_python_datetime(self):
        self.assertEqual(to_python_datetime('20171225'), datetime(2017, 12, 25, 0, 0))
        self.assertEqual(to_python_datetime('20171200'), datetime(2017, 12, 1, 0, 0))
        self.assertEqual(to_python_datetime('20170000'), datetime(2017, 1, 1, 0, 0))
        self.assertRaises(ValueError, to_python_datetime, '2017')

    def test_missing_client(self):
        self.assertRaises(RuntimeError, self.no_anilist._authenticate)
        self.assertFalse(self.no_anilist._is_authenticated())

    @responses.activate
    def test_authentication(self):
        self.add_fake_auth()

        self.assertFalse(self.anilist._is_authenticated())

        auth = self.anilist._authenticate()
        self.assertEqual(auth["access_token"], "fake_token")
        self.assertEqual(auth["token_type"], "Bearer")
        self.assertEqual(auth["expires_in"], 3600)
        self.assertEqual(auth["expires"], 946684800)

    @responses.activate
    def test_get_userlist(self):
        self.add_fake_auth()

        responses.add(
            responses.GET,
            urljoin(AniList.BASE_URL, "user/mrsalixor/animelist"),
            body=self.read_fixture('anilist/mrsalixor_anilist_animelist.json'),
            status=200, content_type='application/json'
        )
        responses.add(
            responses.GET,
            urljoin(AniList.BASE_URL, "user/mrsalixor/mangalist"),
            body=self.read_fixture('anilist/mrsalixor_anilist_mangalist.json'),
            status=200, content_type='application/json',
        )

        anime_list = self.anilist.get_user_list(AniListWorks.animes, 'mrsalixor')
        animes = set(anime_list)
        self.assertEqual(len(animes), 52)

        manga_list = self.anilist.get_user_list(AniListWorks.mangas, 'mrsalixor')
        mangas = set(manga_list)
        self.assertEqual(len(mangas), 57)
