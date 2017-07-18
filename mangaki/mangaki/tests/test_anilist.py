from urllib.parse import urljoin
import os

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.wrappers.anilist import client, AniList, AniListWorks


class AniListTest(TestCase):
    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_DATA_DIR, filename), 'r', encoding='utf-8') as f:
            return f.read()

    def setUp(self):
        self.anilist = client

    @responses.activate
    def test_authentication(self):
        responses.add(
            responses.POST,
            urljoin(AniList.BASE_URL, AniList.AUTH_PATH),
            body='{"access_token":"OMtDiKBVBwe1CRAjge91mMuSzLFG6ChTgRx9LjhO","token_type":"Bearer","expires_in":3600,"expires":1500289907}',
            status=200,
            content_type='application/json'
        )

        auth = self.anilist._authenticate()
        self.assertEqual(auth["access_token"], "OMtDiKBVBwe1CRAjge91mMuSzLFG6ChTgRx9LjhO")
        self.assertEqual(auth["token_type"], "Bearer")
        self.assertEqual(auth["expires_in"], 3600)
        self.assertEqual(auth["expires"], 1500289907)

    @responses.activate
    def test_get_userlist(self):
        responses.add(
            responses.POST,
            urljoin(AniList.BASE_URL, AniList.AUTH_PATH),
            body='{"access_token":"OMtDiKBVBwe1CRAjge91mMuSzLFG6ChTgRx9LjhO","token_type":"Bearer","expires_in":3600,"expires":1500289907}',
            status=200, content_type='application/json'
        )
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
        self.assertEqual(len(animes), 263)

        manga_list = self.anilist.get_user_list(AniListWorks.mangas, 'mrsalixor')
        mangas = set(manga_list)
        self.assertEqual(len(mangas), 57)
