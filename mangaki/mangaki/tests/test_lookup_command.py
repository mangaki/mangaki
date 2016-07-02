from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from mangaki.models import Anime

class LookupTest(TestCase):
    def setUp(self):
        Anime.objects.create(
                title='Steins;Gate',
                source='Ryan'
        )

    def test_lookup_steins_gate(self):
        out = StringIO()

        call_command('lookup', 'Steins;Gate', stdout=out)
        output = out.getvalue().lower()

        self.assertIn(output, 'steins;gate')
        for item in ('like', 'dislike', 'willsee', 'wontsee', 'neutral'):
            self.assertIn(output, item)
