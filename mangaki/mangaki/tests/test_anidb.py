from datetime import datetime
import os

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.models import Category, Editor, Studio, Work, Role, Staff, Artist, TaggedWork, Tag
from mangaki.utils.anidb import client, AniDB


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
        # FIXME: The defaults for editor and studio in Work requires those to
        # exist, or else foreign key constraints fail.
        Editor.objects.create(pk=1)
        # Studio.objects.create(pk=1)
        self.anidb = client
        self.search_fixture = self.read_fixture('search_sangatsu_no_lion.xml')
        self.anime_fixture = self.read_fixture('anidb/sangatsu_no_lion.xml')

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
    def test_anidb_get_multiple_animes(self):
        with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
            rsps.add(
                responses.GET,
                AniDB.BASE_URL,
                body=self.read_fixture('anidb/sangatsu_no_lion.xml'),
                status=200,
                content_type='application/xml'
            )
            rsps.add(
                responses.GET,
                AniDB.BASE_URL,
                body=self.read_fixture('anidb/hibike_euphonium.xml'),
                status=200,
                content_type='application/xml'
            )

            sangatsu = self.anidb.get_or_update_work(11606)
            hibike = self.anidb.get_or_update_work(10889)

        tags_sangatsu = Work.objects.get(pk=sangatsu.pk).taggedwork_set.all()
        tags_sangatsu_titles = tags_sangatsu.values_list('tag__title', flat=True)

        tags_hibike = Work.objects.get(pk=hibike.pk).taggedwork_set.all()
        tags_hibike_titles = tags_hibike.values_list('tag__title', flat=True)

        shared_tags = list(set(tags_sangatsu_titles).intersection(tags_hibike_titles))

        self.assertEqual(sangatsu.title, 'Sangatsu no Lion')
        self.assertEqual(sangatsu.nb_episodes, 22)
        self.assertEqual(sangatsu.studio.title, 'Shaft')
        self.assertEqual(len(tags_sangatsu_titles), 30)

        self.assertEqual(hibike.title, 'Hibike! Euphonium')
        self.assertEqual(hibike.nb_episodes, 13)
        self.assertEqual(hibike.studio.title, 'Kyoto Animation')
        self.assertEqual(len(tags_hibike_titles), 38)

        self.assertCountEqual(shared_tags, ['Japan', 'time', 'Asia', 'comedy',
                                            'themes', 'dynamic', 'Earth', 'cast',
                                            'hard work and guts', 'original work',
                                            'high school', 'following one`s dream',
                                            'elements', 'aim for the top', 'setting',
                                            'school life', 'present', 'place'])

    @responses.activate
    def test_anidb_get(self):
        responses.add(
            responses.GET,
            AniDB.BASE_URL,
            body=self.anime_fixture,
            status=200,
            content_type='application/xml'
        )

        anime = self.anidb.get_or_update_work(11606)
        retrieved_tags = anime.retrieve_tags(self.anidb)

        tags = Work.objects.get(pk=anime.pk).taggedwork_set.all()
        tag_titles = tags.values_list('tag__title', flat=True)

        staff = Work.objects.get(pk=anime.pk).staff_set.all()
        author_names = staff.filter(role__slug='author').values_list('artist__name', flat=True)
        composer_names = staff.filter(role__slug='composer').values_list('artist__name', flat=True)
        director_names = staff.filter(role__slug='director').values_list('artist__name', flat=True)

        self.assertEqual(anime.title, 'Sangatsu no Lion')
        self.assertEqual(anime.nb_episodes, 22)
        self.assertEqual(anime.studio.title, 'Shaft')

        self.assertEqual(anime.date, datetime(2016, 10, 8, 0, 0))
        self.assertEqual(anime.end_date, datetime(2017, 3, 18, 0, 0))

        self.assertCountEqual(author_names, ['Umino Chika'])
        self.assertCountEqual(composer_names, ['Hashimoto Yukari'])
        self.assertCountEqual(director_names, ['Shinbou Akiyuki', 'Okada Kenjirou'])

        self.assertCountEqual(tag_titles, ['seinen', 'high school', 'dynamic', 'target audience',
                                           'themes', 'original work', 'setting', 'elements',
                                           'time', 'place', 'present', 'Earth', 'Japan',
                                           'Tokyo', 'board games', 'manga', 'Asia', 'comedy',
                                           'anthropomorphism', 'school life', 'sports',
                                           'shougi', 'aim for the top', 'funny expressions',
                                           'male protagonist', 'hard work and guts',
                                           'dysfunctional family', 'following one`s dream',
                                           'cast', 'family life'])

        self.assertEqual(len(retrieved_tags["deleted_tags"]), 0)
        self.assertEqual(len(retrieved_tags["added_tags"]), 0)
        self.assertEqual(len(retrieved_tags["updated_tags"]), 0)
        self.assertCountEqual(retrieved_tags["kept_tags"], tag_titles)

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
