from io import StringIO
import responses
import os.path
import logging
import re

from django.test import TestCase
from django.core import management
from django.conf import settings
from mangaki.models import Work, Category, Artist


class CommandTest(TestCase):
    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_DATA_DIR, filename), 'r') as f:
            return f.read()

    def setUp(self):
        self.anime = Work.objects.create(
                        anidb_aid=3651,
                        ext_poster='https://mangaki.fr/static/img/favicon.png',
                        category=Category.objects.get(slug='anime'),
                        title='La Mélancolie de Haruhi Suzumiya')
        self.album = Work.objects.create(
                        vgmdb_aid=22495,
                        category=Category.objects.get(slug='album'),
                        title='BLUE')
        self.artist = Artist.objects.create(name='Yoko Kanno')
        self.album_fixture = self.read_fixture('blue_vgmdb.json')
        self.stdout = StringIO()

    def test_add_anidb(self):
        management.call_command('add_anidb', 12994, stdout=self.stdout)
        self.assertEquals(self.stdout.getvalue(),
                          "Successfully added Sangatsu no Lion (2017)\n")

    def test_anidb_tags_to_json(self):
        management.call_command('anidb_tags_to_json', self.anime.id,
                                stdout=self.stdout)
        self.assertIn('---', self.stdout.getvalue())

    def test_compare(self):
        management.call_command('compare', 'mangas', stdout=self.stdout)
        self.assertTrue(True)

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
        management.call_command('lookup', 'haruhi', stdout=self.stdout)
        self.assertIn(str(self.anime.id), self.stdout.getvalue())

    def test_ranking(self):
        management.call_command('ranking')
        self.assertTrue(True)

    def test_retrieveposters(self):
        management.call_command('retrieveposters', self.anime.id,
                                stdout=self.stdout)
        self.assertEquals(self.stdout.getvalue(),
                          '1 poster(s) successfully downloaded.\n')

    def test_tokens(self):
        management.call_command('tokens', 'DR', '--salt', 'PEPPER',  # HA HA
                                stdout=self.stdout)
        self.assertEquals(self.stdout.getvalue(),
                          'DR a2c8126e2a2c7b0bb8cac57577e16f9ddc9971f9\n')

    @responses.activate
    def test_vgmdb(self):
        responses.add(
            responses.GET,
            re.compile(r'http://vgmdb.info/album/.*?format=json'),
            body=self.album_fixture,
            status=200,
            content_type='application/json'
        )
        management.call_command('vgmdb', self.album.id,
                                stdout=self.stdout)
        self.assertEquals(self.stdout.getvalue(),
                          'Successfully added Yoko Kanno to '
                          'COWBOY BEBOP Original Soundtrack 3 BLUE\n')
