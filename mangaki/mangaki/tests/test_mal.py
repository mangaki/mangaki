import os
import re

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.utils.mal import MALClient, MALWorks


class MALTest(TestCase):
    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_DATA_DIR, filename), 'r') as f:
            return f.read()

    def setUp(self):
        self.mal = MALClient('test_client', 'test_client')
        self.search_fixture = self.read_fixture('code_geass_mal_search.xml')
        self.list_fixture = self.read_fixture('raitobezarius_mal.xml')

    @responses.activate
    def test_mal_search_one_work(self):
        responses.add(
            responses.GET,
            re.compile('https?://myanimelist\.net/api/.*/search.xml\?q=.*'),
            body=self.search_fixture,
            status=200,
            content_type='application/xml'
        )
        anime_query = 'code geass'
        result = self.mal.search_work(MALWorks.animes, anime_query)
        self.assertEqual(result.work_type, MALWorks.animes)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_mal_list_works_from_a_user(self):
        responses.add(
            responses.GET,
            re.compile('https?://myanimelist\.net/malappinfo.php\?.*'),
            body=self.list_fixture,
            status=200,
            content_type='application/xml'
        )
        results = list(self.mal.list_works_from_a_user(MALWorks.animes, 'raitobezarius'))

        self.assertNotEqual(len(results), 0)
        self.assertEqual(len(responses.calls), 1)
