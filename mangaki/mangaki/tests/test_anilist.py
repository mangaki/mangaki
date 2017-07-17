from urllib.parse import urljoin

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.wrappers.anilist import client, AniList


class AniListTest(TestCase):
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
