from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO

from mangaki.models import Work, Category, Editor, Studio

class LookupTest(TestCase):
    def setUp(self):
        # FIXME: The defaults for editor and studio in Work requires those to
        # exist, or else foreign key constraints fail.
        Editor.objects.create(pk=1)
        Studio.objects.create(pk=1)

        anime = Category.objects.get(slug='anime')
        Work.objects.create(
            title='Steins;Gate',
            source='Ryan',
            category=anime
        )

    def test_lookup_steins_gate(self):
        out = StringIO()

        call_command('lookup', 'Steins;Gate', stdout=out)
        output = out.getvalue().lower()

        self.assertIn(output, 'steins;gate')
        for item in ('like', 'dislike', 'willsee', 'wontsee', 'neutral'):
            self.assertIn(output, item)
