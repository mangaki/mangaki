from urllib.parse import urljoin

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.wrappers.anilist import client, AniList


class AniListTest(TestCase):
    def setUp(self):
        self.anilist = client
        self.fake_auth_json = '{"access_token":"fake_token","token_type":"Bearer","expires_in":3600,"expires":946684800}'

    @responses.activate
    def test_authentication(self):
        responses.add(
            responses.POST,
            urljoin(AniList.BASE_URL, AniList.AUTH_PATH),
            body=self.fake_auth_json,
            status=200,
            content_type='application/json'
        )

        auth = self.anilist._authenticate()
        self.assertEqual(auth["access_token"], "fake_token")
        self.assertEqual(auth["token_type"], "Bearer")
        self.assertEqual(auth["expires_in"], 3600)
        self.assertEqual(auth["expires"], 946684800)
