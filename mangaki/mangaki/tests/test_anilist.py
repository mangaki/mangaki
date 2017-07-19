from datetime import datetime
from urllib.parse import urljoin
import os

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.wrappers.anilist import to_anime_season, client, AniList, AniListStatus


class AniListTest(TestCase):
    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_DATA_DIR, filename), 'r', encoding='utf-8') as f:
            return f.read()

    def setUp(self):
        self.anilist = client

    def test_to_anime_season(self):
        self.assertEqual(to_anime_season(datetime(2017, 1, 1, 0, 0)), 'winter')
        self.assertEqual(to_anime_season(datetime(2017, 4, 1, 0, 0)), 'spring')
        self.assertEqual(to_anime_season(datetime(2017, 7, 1, 0, 0)), 'summer')
        self.assertEqual(to_anime_season(datetime(2017, 10, 1, 0, 0)), 'fall')

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
    def test_get_seasonal_anime(self):
        responses.add(
            responses.POST,
            urljoin(AniList.BASE_URL, AniList.AUTH_PATH),
            body='{"access_token":"OMtDiKBVBwe1CRAjge91mMuSzLFG6ChTgRx9LjhO","token_type":"Bearer","expires_in":3600,"expires":1500289907}',
            status=200,
            content_type='application/json'
        )
        responses.add(
            responses.GET,
            urljoin(AniList.BASE_URL, 'browse/anime'),
            body=self.read_fixture('anilist/airing_summer_2017_trimmed.json'),
            status=200, content_type='application/json'
        )

        for anime in self.anilist.list_seasonal_animes(year=2017, season='summer'):
            if anime.title == 'Made in Abyss':
                self.assertEqual(anime.anilist_id, 97986)
                self.assertEqual(anime.english_title, 'Made in Abyss')
                self.assertEqual(anime.japanese_title, 'メイドインアビス')
                self.assertEqual(anime.media_type, 'TV')
                self.assertEqual(anime.start_date, datetime(2017, 7, 7))
                self.assertIsNone(anime.end_date)
                self.assertEqual(anime.synonyms, [])
                self.assertEqual(anime.genres, ['Adventure', 'Fantasy', 'Sci-Fi'])
                self.assertFalse(anime.is_nsfw)
                self.assertEqual(anime.poster_url, 'https://cdn.anilist.co/img/dir/anime/reg/97986-ZL0DkAyNWyxG.jpg')
                self.assertEqual(anime.nb_episodes, 13)
                self.assertEqual(anime.status, AniListStatus.airing)
                self.assertEqual(anime.tags[1], {'anilist_tag_id': 175, 'name': 'Robots', 'spoiler': False})
                break
