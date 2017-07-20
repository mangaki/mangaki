from datetime import datetime
import os

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.models import Category, Editor, Studio, Work, Role, Staff, Artist, TaggedWork, Tag
from mangaki.utils.anidb import to_python_datetime, AniDB


class AniDBTest(TestCase):
    @staticmethod
    def create_anime(**kwargs):
        anime = Category.objects.get(slug='anime')
        return Work.objects.create(category=anime, **kwargs)

    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_DATA_DIR, filename), 'r', encoding='utf-8') as f:
            return f.read()

    def setUp(self):
        self.anidb = AniDB('test_client', 1)
        self.no_anidb = AniDB()
        self.search_fixture = self.read_fixture('search_sangatsu_no_lion.xml')
        self.anime_fixture = self.read_fixture('anidb/sangatsu_no_lion.xml')

    def test_to_python_datetime(self):
        self.assertEqual(to_python_datetime('2017-12-25'), datetime(2017, 12, 25, 0, 0))
        self.assertEqual(to_python_datetime('2017-12'), datetime(2017, 12, 1, 0, 0))
        self.assertEqual(to_python_datetime('2017'), datetime(2017, 1, 1, 0, 0))
        self.assertRaises(ValueError, to_python_datetime, '2017-25')

    def test_missing_client(self):
        self.assertRaises(RuntimeError, self.no_anidb._request, 'dummypage')
        self.assertFalse(self.no_anidb.is_available)

    @responses.activate
    def test_anidb_search(self):
        responses.add(
            responses.GET,
            AniDB.SEARCH_URL,
            body=self.search_fixture,
            status=200,
            content_type='application/xml'
        )
        anime_query = 'sangatsu no lion'
        results = self.anidb.search(q=anime_query)
        self.assertEqual(len(results), 2)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_anidb_get_animes(self):
        # Fake an artist entry with no AniDB creator ID that will be filled by retrieving Sangatsu
        artist = Artist(name="Shinbou Akiyuki").save()

        filenames = ['anidb/sangatsu_no_lion.xml', 'anidb/sangatsu_no_lion.xml', 'anidb/hibike_euphonium.xml']
        with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
            for filename in filenames:
                rsps.add(
                    responses.GET,
                    AniDB.BASE_URL,
                    body=self.read_fixture(filename),
                    status=200,
                    content_type='application/xml'
                )

            sangatsu = self.anidb.get_or_update_work(11606)
            retrieved_tags_sangatsu = sangatsu.retrieve_tags(self.anidb)
            hibike = self.anidb.get_or_update_work(10889)

        # Retrieve tags
        tags_sangatsu = set(Work.objects.get(pk=sangatsu.pk).taggedwork_set.all().values_list('tag__title', flat=True))
        tags_hibike = set(Work.objects.get(pk=hibike.pk).taggedwork_set.all().values_list('tag__title', flat=True))
        shared_tags = tags_sangatsu.intersection(tags_hibike)

        # Checks on tags
        self.assertEqual(len(tags_sangatsu), 30)
        self.assertEqual(len(tags_hibike), 38)
        self.assertEqual(len(shared_tags), 18)

        # Check for Sangatsu's informations
        self.assertEqual(sangatsu.title, 'Sangatsu no Lion')
        self.assertEqual(sangatsu.nb_episodes, 22)
        self.assertEqual(sangatsu.studio.title, 'Shaft')
        self.assertEqual(sangatsu.date, datetime(2016, 10, 8, 0, 0))
        self.assertEqual(sangatsu.end_date, datetime(2017, 3, 18, 0, 0))

        # Check for Sangatsu's staff
        staff_sangatsu = Work.objects.get(pk=sangatsu.pk).staff_set.all().values_list('artist__name', flat=True)
        self.assertCountEqual(staff_sangatsu, ['Umino Chika', 'Hashimoto Yukari', 'Shinbou Akiyuki', 'Okada Kenjirou'])

        # Check retrieved tags from AniDB
        self.assertEqual(len(retrieved_tags_sangatsu["deleted_tags"]), 0)
        self.assertEqual(len(retrieved_tags_sangatsu["added_tags"]), 0)
        self.assertEqual(len(retrieved_tags_sangatsu["updated_tags"]), 0)
        self.assertEqual(len(retrieved_tags_sangatsu["kept_tags"]), len(tags_sangatsu))

        # Check for no artist duplication
        artist = Artist.objects.filter(name="Shinbou Akiyuki")
        self.assertEqual(artist.count(), 1)
        self.assertEqual(artist.first().anidb_creator_id, 59)

    @responses.activate
    def test_anidb_nsfw(self):
        animes = {}

        animes_sources = {
            # Not NSFW at all
            'anidb/sangatsu_no_lion.xml': (11606, 'Sangatsu no Lion'),
            'anidb/hibike_euphonium.xml': (10889, 'Hibike! Euphonium'),
            # Totally NSFW (restricted on AniDB)
            'anidb/boku_no_piko.xml': (4544, 'Boku no Piko'),
            'anidb/bible_black.xml': (528, 'Bible Black'),
            # Should be marked NSFW
            'anidb/r15.xml': (8396, 'R-15'),
            'anidb/astarotte_no_omocha_ex.xml': (8560, 'Astarotte no Omocha! EX'),
            'anidb/aki_sora.xml': (6782, 'Aki Sora'),
            # Shouldn't be marked NSFW
            'anidb/punchline.xml': (10948, 'Punch Line'),
            'anidb/panty_stocking.xml': (7529, 'Panty & Stocking with Garterbelt'),
            'anidb/shimoneta.xml': (10888, 'Shimoneta to Iu Gainen ga Sonzai Shinai Taikutsu na Sekai')
        }

        are_nsfw = ['anidb/boku_no_piko.xml', 'anidb/bible_black.xml',
                    'anidb/r15.xml', 'anidb/astarotte_no_omocha_ex.xml',
                    'anidb/aki_sora.xml']
        are_sfw = ['anidb/sangatsu_no_lion.xml', 'anidb/hibike_euphonium.xml',
                   'anidb/punchline.xml', 'anidb/panty_stocking.xml',
                   'anidb/shimoneta.xml']

        with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
            for filename, infos in animes_sources.items():
                rsps.add(
                    responses.GET,
                    AniDB.BASE_URL,
                    body=self.read_fixture(filename),
                    status=200,
                    content_type='application/xml'
                )
                animes[filename] = self.anidb.get_or_update_work(infos[0])

        for filename in are_nsfw:
            with self.subTest('Asserting NSFW', anime=animes_sources[filename][1]):
                self.assertEqual(animes[filename].title, animes_sources[filename][1])
                self.assertTrue(animes[filename].nsfw)

        for filename in are_sfw:
            with self.subTest('Asserting SFW', anime=animes_sources[filename][1]):
                self.assertEqual(animes[filename].title, animes_sources[filename][1])
                self.assertFalse(animes[filename].nsfw)
