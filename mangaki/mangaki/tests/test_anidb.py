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
        self.anime_fixture = self.read_fixture('sangatsu_no_lion.xml')

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
