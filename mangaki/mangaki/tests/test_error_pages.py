from django.test import TestCase, Client
from mangaki.models import Work, Category, Trope, Editor, Studio


class ErrorPageTest(TestCase):

    def setUp(self):
        # FIXME: The defaults for editor and studio in Work requires those to
        # exist, or else foreign key constraints fail.
        Editor.objects.create(pk=1)
        Studio.objects.create(pk=1)

        self.client = Client()
        anime = Category.objects.get(slug='anime')
        work = Work.objects.create(
            title='Initial D',
            source='Fujiwara Bunta',
            category=anime
        )
        trope = Trope.objects.create(
            trope='INERTIA DORIFTU ?!',
            author='Keisuke Takahashi',
            origin=work
        )
        self.work = work
        self.trope = trope

    def get_404_url():
        return '/does/not/exist/'

    def test_trope(self):
        response = self.client.get(self.get_404_url())
        self.assertEqual(response.status_code, 404)
        self.assertIn(self.trope.trope, str(response.content))

    def test_no_trope(self):  # An error 500 could occur in this case.
        self.trope.delete()
        response = self.client.get(self.get_404_url())
        self.assertEqual(response.status_code, 404)
