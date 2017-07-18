from datetime import datetime
from urllib.parse import urljoin

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.wrappers.anilist import to_python_datetime, AniList


class AniListTest(TestCase):
    def setUp(self):
        self.anilist = AniList('test_client', 'client_secret')
        self.no_anilist = AniList()
        self.fake_auth_json = '{"access_token":"fake_token","token_type":"Bearer","expires_in":3600,"expires":946684800}'

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
        responses.add(
            responses.POST,
            urljoin(AniList.BASE_URL, AniList.AUTH_PATH),
            body=self.fake_auth_json,
            status=200,
            content_type='application/json'
        )

        self.assertFalse(self.anilist._is_authenticated())

        auth = self.anilist._authenticate()
        self.assertEqual(auth["access_token"], "fake_token")
        self.assertEqual(auth["token_type"], "Bearer")
        self.assertEqual(auth["expires_in"], 3600)
        self.assertEqual(auth["expires"], 946684800)
