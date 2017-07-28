from datetime import datetime
from urllib.parse import urljoin
import os

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.models import Work, Language, ExtLanguage
from mangaki.wrappers.anilist import to_python_datetime, to_anime_season, AniList, AniListStatus, AniListWorks, AniListException, insert_works_into_database_from_anilist


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

    def setUp(self):
        self.anilist = AniList('test_client', 'client_secret')
        self.no_anilist = AniList()

    def test_to_python_datetime(self):
        self.assertEqual(to_python_datetime('20171225'), datetime(2017, 12, 25, 0, 0))
        self.assertEqual(to_python_datetime('20171200'), datetime(2017, 12, 1, 0, 0))
        self.assertEqual(to_python_datetime('20170000'), datetime(2017, 1, 1, 0, 0))
        self.assertRaises(ValueError, to_python_datetime, '2017')

    def test_to_anime_season(self):
        self.assertEqual(to_anime_season(datetime(2017, 1, 1, 0, 0)), 'winter')
        self.assertEqual(to_anime_season(datetime(2017, 4, 1, 0, 0)), 'spring')
        self.assertEqual(to_anime_season(datetime(2017, 7, 1, 0, 0)), 'summer')
        self.assertEqual(to_anime_season(datetime(2017, 10, 1, 0, 0)), 'fall')

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
    def test_api_errors(self):
        self.add_fake_auth()

        error_tests = [{
            'route': 'unknown_route', 'status': 404, 'exception': '"unknown_route" API route does not exist',
            'body': '{"error":{"status":404,"messages":["API route not found."]}}'
        },
        {
            'route': 'token_expired', 'status': 200, 'exception': 'token no longer valid or not found',
            'body': '{"error":"access_denied","error_description":"The resource owner or authorization server denied the request."}'
        },
        {
            'route': 'token_missing', 'status': 401, 'exception': 'token no longer valid or not found',
            'body': '{"status":401,"error":"unauthorized","error_message":"Access token is missing"}'
        },
        {
            'route': 'other_error', 'status': 404, 'exception': 'unknown_error - handle too',
            'body': '{"status":404,"error":{"unknown_error":"handle too"}}'
        }]

        for error_test in error_tests:
            with self.subTest(error_test['route'], exception=error_test['exception']):
                responses.add(
                    responses.GET, urljoin(AniList.BASE_URL, error_test['route']),
                    body=error_test['body'], status=error_test['status'], content_type='application/json'
                )

                with self.assertRaisesRegexp(AniListException, error_test['exception']):
                    self.anilist._request(error_test['route'])

    @responses.activate
    def test_get_seasonal_anime(self):
        self.add_fake_auth()

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
                self.assertIsNone(anime.description)
                self.assertEqual(anime.synonyms, [])
                self.assertEqual(anime.genres, ['Adventure', 'Fantasy', 'Sci-Fi'])
                self.assertFalse(anime.is_nsfw)
                self.assertEqual(anime.poster_url, 'https://cdn.anilist.co/img/dir/anime/reg/97986-ZL0DkAyNWyxG.jpg')
                self.assertEqual(anime.nb_episodes, 13)
                self.assertEqual(anime.status, AniListStatus.airing)
                self.assertEqual(anime.tags[1], {'anilist_tag_id': 175, 'name': 'Robots', 'spoiler': False, 'votes': 53})
                break

    @responses.activate
    def test_get_work_by_id(self):
        self.add_fake_auth()

        responses.add(
            responses.GET,
            urljoin(AniList.BASE_URL, 'anime/20912/page'),
            body=self.read_fixture('anilist/hibike_euphonium.json'),
            status=200, content_type='application/json'
        )

        hibike = self.anilist.get_work_by_id(AniListWorks.animes, 20912)

        self.assertEqual(hibike.english_title, 'Sound! Euphonium')
        self.assertEqual(hibike.japanese_title, '響け！ユーフォニアム')
        self.assertEqual(hibike.studio, 'Kyoto Animation')
        self.assertEqual(hibike.episode_length, 24)

        self.assertEqual(hibike.youtube_url, 'https://www.youtube.com/watch?v=r_Kk9xhVkB8')
        self.assertEqual(hibike.crunchyroll_url, 'http://www.crunchyroll.com/sound-euphonium')
        self.assertEqual(hibike.twitter_url, 'https://twitter.com/anime_eupho')
        self.assertEqual(hibike.official_url, 'http://anime-eupho.com/')

        responses.add(
            responses.GET,
            urljoin(AniList.BASE_URL, 'anime/99999999999/page'),
            body='{"error":{"status":404,"messages":["No query results for model [App/AniList/v1/Series/Series] 99999999999"]}}',
            status=404, content_type='application/json'
        )

        inexistant_work = self.anilist.get_work_by_id(AniListWorks.animes, 99999999999)
        self.assertIsNone(inexistant_work)

    @responses.activate
    def test_get_work_by_title(self):
        self.add_fake_auth()

        responses.add(
            responses.GET,
            urljoin(AniList.BASE_URL, 'anime/search/Hibike!'),
            body=self.read_fixture('anilist/hibike_euphonium_search.json'),
            status=200, content_type='application/json'
        )

        hibike = self.anilist.get_work_by_title(AniListWorks.animes, 'Hibike!')

        self.assertEqual(hibike.english_title, 'Sound! Euphonium')
        self.assertEqual(hibike.japanese_title, '響け！ユーフォニアム')

        responses.add(
            responses.GET,
            urljoin(AniList.BASE_URL, 'anime/search/no%20such%20anime'),
            body='{"error":{"status":200,"messages":["No Results."]}}',
            status=200, content_type='application/json'
        )

        inexistant_work = self.anilist.get_work_by_title(AniListWorks.animes, 'no such anime')
        self.assertIsNone(inexistant_work)

    @responses.activate
    def test_get_userlist(self):
        self.add_fake_auth()

        for work_type in AniListWorks:
            responses.add(
                responses.GET,
                urljoin(AniList.BASE_URL, 'user/mrsalixor/{}list'.format(work_type.value)),
                body=self.read_fixture('anilist/mrsalixor_anilist_{}list.json'.format(work_type.value)),
                status=200, content_type='application/json'
            )

        anime_list = self.anilist.get_user_list(AniListWorks.animes, 'mrsalixor')
        animes = set(anime_list)
        self.assertEqual(len(animes), 52)

        manga_list = self.anilist.get_user_list(AniListWorks.mangas, 'mrsalixor')
        mangas = set(manga_list)
        self.assertEqual(len(mangas), 57)

        for work_type in AniListWorks:
            responses.add(
                responses.GET,
                urljoin(AniList.BASE_URL, 'user/aaaaaaaaaaaaa/{}list'.format(work_type.value)),
                body='{"error":{"status":404,"messages":["No query results for model [App/AniList/v1/User/User] aaaaaaaaaaaaa"]}}',
                status=404, content_type='application/json'
            )

        inexistant_user_animelist = list(self.anilist.get_user_list(AniListWorks.animes, 'aaaaaaaaaaaaa'))
        inexistant_user_mangalist = list(self.anilist.get_user_list(AniListWorks.mangas, 'aaaaaaaaaaaaa'))
        self.assertCountEqual(inexistant_user_animelist, [])
        self.assertCountEqual(inexistant_user_mangalist, [])

    @responses.activate
    def test_insert_into_database(self):
        self.add_fake_auth()

        responses.add(
            responses.GET,
            urljoin(AniList.BASE_URL, 'browse/anime'),
            body=self.read_fixture('anilist/airing_summer_2017_trimmed.json'),
            status=200, content_type='application/json'
        )

        seasonal = list(self.anilist.list_seasonal_animes(year=2017, season='summer'))
        self.assertEqual(len(insert_works_into_database_from_anilist(seasonal)), 7)
