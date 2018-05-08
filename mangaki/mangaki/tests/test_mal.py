import os
import re
from unittest.mock import patch

import redis
import responses
from django.conf import settings
from django.contrib.auth.models import User
from hypothesis.extra.django import TestCase

from mangaki import tasks
from mangaki.models import UserBackgroundTask
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
        self.user, _ = User.objects.get_or_create(
            username='Raito_Bezarius'
        )

    @given(choice=st.choices(),
           query=st.text())
    @responses.activate
    def test_mal_client_exceptions(self, choice, query):
        work_type = MALWorks(choice(list(map(lambda x: x.value, MALWorks))))
        catch_all = re.compile('https?://myanimelist\.net/api/.*')
        for status_code in [400, 401, 403, 500, 502]:
            with self.subTest("Testing {} status code through MAL API search wrapper".format(status_code),
                              status_code=status_code):
                responses.add(
                    responses.GET,
                    catch_all,
                    status=status_code
                )
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
        # We should be able to be test-data-agnostic.
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

        from mangaki.utils.mal import logger as mal_logger
        with self.assertLogs(logger=mal_logger, level='ERROR'):
            results = list(self.mal.list_works_from_a_user(MALWorks.animes, 'raitobezarius'))
            self.assertEqual(len(results), 0)

    @patch('mangaki.utils.mal.import_mal')
    @patch('redis.StrictRedis', autospec=True, create=True)
    def test_mal_task_cleanup(self, strict_redis, import_mal_operation):
        tasks.import_mal.push_request(id=1)

        with self.subTest('When the import succeeds, there is no background task anymore, nor Redis task details.'):
            tasks.import_mal.run('RaitoBezarius',
                                 self.user.username)
            r = strict_redis.return_value
            self.assertTrue(r.delete.called)
            self.assertFalse(self.user.background_tasks.exists())

        with self.subTest('When the import fails, there is no background task anymore, nor Redis task details.'):
            import_mal_operation.side_effect = Exception('Boom !')
            with self.assertRaises(Exception):
                tasks.import_mal.run('RaitoBezarius',
                                     self.user.username)

            r = strict_redis.return_value
            self.assertTrue(r.delete.called)
            self.assertFalse(self.user.background_tasks.exists())

    @patch('redis.StrictRedis', autospec=True, create=True)
    @patch('mangaki.utils.mal.import_mal')
    def test_mal_task_multiple_start(self, import_mal_operation, strict_redis):
        bg_task, created = UserBackgroundTask.objects.get_or_create(owner=self.user,
                                                                    tag=tasks.MAL_IMPORT_TAG)

        self.assertTrue(created)

        tasks.import_mal('RaitoBezarius',
                         self.user.username)
        r = strict_redis.return_value
        bg_task.delete()

        self.assertFalse(r.set.called)
        import_mal_operation.assert_not_called()
