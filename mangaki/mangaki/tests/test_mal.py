import os
import re
import xml.etree.ElementTree as ET
from unittest.mock import patch

import responses
from django.conf import settings
from django.contrib.auth.models import User
from hypothesis.extra.django import TestCase

from mangaki import tasks
from mangaki.models import UserBackgroundTask, Work, WorkTitle
from mangaki.utils.mal import MALClient, MALWorks, MALUserWork, MALEntry

from hypothesis import given
from hypothesis import strategies as st


class MALTest(TestCase):
    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_DATA_DIR, filename), 'r') as f:
            return f.read()

    def setUp(self):
        self.mal = MALClient('test_client', 'test_client')
        self.search_fixture = self.read_fixture('mal/code_geass_search.xml')
        self.list_fixture = self.read_fixture('mal/raitobezarius_mal.xml')

        self.steins_gate_xml = ET.fromstring(self.read_fixture('mal/steins_gate_entry.xml'))
        self.steins_gate_zero_xml = ET.fromstring(self.read_fixture('mal/steins_gate_zero_entry.xml'))
        self.steins_gate_movie_xml = ET.fromstring(self.read_fixture('mal/steins_gate_movie_entry.xml'))
        self.darling_in_the_franxx_xml = ET.fromstring(self.read_fixture('mal/darling_in_the_franxx_entry.xml'))

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

    @patch('mangaki.utils.mal.client', autospec=True, create=True)
    @given(st.randoms())
    def test_mal_duplication(self, client_mock, rand):
        from mangaki.utils.mal import import_mal
        # prepare list of animes
        steins_gate_entry = MALEntry(self.steins_gate_xml, MALWorks.animes)
        darling_entry = MALEntry(self.darling_in_the_franxx_xml, MALWorks.animes)
        steins_gate_movie_entry = MALEntry(self.steins_gate_movie_xml, MALWorks.animes)
        steins_gate_zero_entry = MALEntry(self.steins_gate_zero_xml, MALWorks.animes)

        mal_user_works = [
            MALUserWork(steins_gate_entry.title, steins_gate_entry.synonyms, 'mal_something',
                        str(steins_gate_entry.mal_id),
                        10,
                        2),
            MALUserWork(darling_entry.title, darling_entry.synonyms, 'zero_two',
                        str(steins_gate_entry.mal_id),
                        10,
                        1),
            MALUserWork(steins_gate_movie_entry.title, steins_gate_movie_entry.synonyms, 'non_canon',
                        str(steins_gate_movie_entry.mal_id),
                        5,
                        2),
            MALUserWork(steins_gate_zero_entry.title, steins_gate_zero_entry.synonyms, 'brain_science_institute',
                        str(steins_gate_zero_entry.mal_id),
                        10,
                        1)
        ]

        search_results = {
            steins_gate_entry.title: [steins_gate_movie_entry, steins_gate_entry, steins_gate_zero_entry],
            darling_entry.title: [darling_entry],
            steins_gate_zero_entry.title: [steins_gate_zero_entry, steins_gate_movie_entry],
            steins_gate_movie_entry.title: [steins_gate_movie_entry]
        }

        # Here, we shuffle lists. using Hypothesis' controlled Random instance.
        rand.shuffle(search_results[steins_gate_entry.title])
        rand.shuffle(search_results[steins_gate_zero_entry.title])

        client_mock.list_works_from_a_user.return_value = (item for item in mal_user_works)
        client_mock.search_works.side_effect = lambda _, query: search_results.get(query, [])

        import_mal(self.user.username, self.user.username)
        n_works = Work.objects.count()
        expected = len(mal_user_works)

        # Assumption: all users' works were imported.
        self.assertEqual(n_works, expected)

        # Kill the WorkTitle. Remove evidences.
        WorkTitle.objects.all().delete()

        for _ in range(3):
            # Reset mocks.
            client_mock.list_works_from_a_user.return_value = (item for item in mal_user_works)
            client_mock.search_works.side_effect = lambda _, query: search_results.get(query, [])

            import_mal(self.user.username, self.user.username)

        # Assumption: no duplicates.
        self.assertEqual(n_works, Work.objects.count())

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
