from io import StringIO
import responses
import os.path
import logging
import re

from django.test import TestCase
from django.core import management
from django.conf import settings
from mangaki.models import Work, Category, Artist
from mangaki.utils.anidb import AniDB
from mangaki.wrappers.anilist import AniList
from mangaki.utils.tokens import compute_token


class CommandTest(TestCase):
    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_DATA_DIR, filename), 'r') as f:
            return f.read()

    def setUp(self):
        self.anime = Work.objects.create(
                        anidb_aid=11606,
                        ext_poster='https://mangaki.fr/static/img/favicon.png',
                        category=Category.objects.get(slug='anime'),
                        title='Sangatsu no Lion')
        self.anidb_fixture = self.read_fixture('anidb/sangatsu_no_lion.xml')
        self.anilist_fixture = self.read_fixture('anilist/hibike_euphonium.json')
        self.album = Work.objects.create(
                        vgmdb_aid=22495,
                        category=Category.objects.get(slug='album'),
                        title='BLUE')
        self.album_fixture = self.read_fixture('blue_vgmdb.json')
        self.artist = Artist.objects.create(name='Yoko Kanno')
        self.stdout = StringIO()

    @responses.activate
    def test_add_anidb(self):
        responses.add(
            responses.GET,
            AniDB.BASE_URL,
            body=self.anidb_fixture,
            status=200,
            content_type='application/xml'
        )
        management.call_command('add_anidb', self.anime.anidb_aid,
                                stdout=self.stdout)
        self.assertEquals(self.stdout.getvalue(),
                          "Successfully added Sangatsu no Lion\n")

    @responses.activate
    def test_anidb_tags_to_json(self):
        responses.add(
            responses.GET,
            AniDB.BASE_URL,
            body=self.anidb_fixture,
            status=200,
            content_type='application/xml'
        )
        management.call_command('anidb_tags_to_json', self.anime.id,
                                stdout=self.stdout)
        self.assertIn('---', self.stdout.getvalue())

    @responses.activate
    def test_anilist_tags_to_json(self):
        responses.add(
            responses.GET,
            AniList.BASE_URL,
            body=self.anilist_fixture,
            status=200,
            content_type='application/json'
        )
        management.call_command('anilist_tags_to_json', self.anime.id,
                                stdout=self.stdout)
        self.assertIn('---', self.stdout.getvalue())

    def test_fit_algo(self):
        management.call_command('fit_algo', 'zero', stdout=self.stdout)
        self.assertEquals(self.stdout.getvalue(),
                          "Successfully fit zero (0.0 MB)\n")

    def test_generate_seed_data(self):
        management.call_command('generate_seed_data', 'small',
                                stdout=self.stdout)
        self.assertEquals(self.stdout.getvalue(), 'Fixture ready.\n')

    def test_lastactivity(self):
        management.call_command('lastactivity')
        self.assertTrue(True)

    def test_lookup(self):
        management.call_command('lookup', 'lion', stdout=self.stdout)
        self.assertIn(str(self.anime.id), self.stdout.getvalue())

    def test_ranking(self):
        management.call_command('ranking')
        self.assertTrue(True)

    @responses.activate
    def test_retrieveposters(self):
        responses.add(
            responses.GET,
            re.compile(r'https://mangaki\.fr/.*'),
            body=self.anidb_fixture,
            status=200,
            content_type='application/xml'
        )
        management.call_command('retrieveposters', self.anime.id,
                                stdout=self.stdout)
        self.assertEquals(self.stdout.getvalue(),
                          '1 poster(s) successfully downloaded.\n')

    def test_tokens(self):
        management.call_command('tokens', 'DR', '--salt', 'PEPPER',  # HA HA
                                stdout=self.stdout)
        self.assertEquals(self.stdout.getvalue(),
                          'DR {:s}\n'.format(compute_token('PEPPER', 'DR')))

    def test_top(self):
        management.call_command('top', '--all', stdout=self.stdout)
        self.assertEquals(len(self.stdout.getvalue().splitlines()), 6)

    @responses.activate
    def test_vgmdb(self):
        responses.add(
            responses.GET,
            re.compile(r'http://vgmdb\.info/.*'),
            body=self.album_fixture,
            status=200,
            content_type='application/json'
        )
        management.call_command('vgmdb', self.album.id,
                                stdout=self.stdout)
        self.assertEquals(self.stdout.getvalue(),
                          'Successfully added Yoko Kanno to '
                          'COWBOY BEBOP Original Soundtrack 3 BLUE\n')
