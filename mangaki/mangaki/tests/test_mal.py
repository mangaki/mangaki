import os
import re

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.utils.mal import MALClient, MALWorks

from hypothesis import given
from hypothesis import strategies as st


class MALTest(TestCase):
    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_DATA_DIR, filename), 'r') as f:
            return f.read()

    def setUp(self):
        self.mal = MALClient('test_client', 'test_client')
        self.search_fixture = self.read_fixture('code_geass_mal_search.xml')
        self.list_fixture = self.read_fixture('raitobezarius_mal.xml')

    @given(choice=st.choices(),
           query=st.text())
    @responses.activate
    def test_mal_client_exceptions(self, choice, query):
        work_type = MALWorks(choice(list(map(lambda x: x.value, MALWorks))))
        catch_all = re.compile('https?://myanimelist\.net/api/.*')
        statuses = [400, 401, 403, 500, 502]
        for status in statuses:
            responses.add(
                responses.GET,
                catch_all,
                status=status
            )

        for _ in statuses:
            with self.assertRaisesRegex(RuntimeError,
                                        r'(Invalid MAL credentials!)|(MAL request failure!)'):
                self.mal.search_works(work_type, query)

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

        # FIXME: rather clunky, we should move this into another test.
        # and control the original XML.
        self.assertNotEqual(result.start_date, None)
        self.assertEqual(result.synonyms, [])
        self.assertEqual(result.nb_episodes, 25)
        self.assertNotEqual(result.poster, None)
        self.assertEqual(result.title, 'Code Geass: Hangyaku no Lelouch')
        self.assertEqual(
            result.english_title,
            'Code Geass: Lelouch of the Rebellion'
        )
        self.assertNotEqual(result.source_url, None)
        self.assertNotEqual(result.mal_id, None)

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

    @responses.activate
    def test_mal_malformed_xml(self):
        responses.add(
            responses.GET,
            re.compile('https?://myanimelist\.net/malappinfo.php\?.*'),
            body='<xml><myinfo>42</myinfo><anime></anime></xml>',
            status=200,
            content_type='application/xml'
        )

        with self.assertLogs(level='ERROR'):
            results = list(self.mal.list_works_from_a_user(MALWorks.animes, 'raitobezarius'))
            self.assertEqual(len(results), 0)
