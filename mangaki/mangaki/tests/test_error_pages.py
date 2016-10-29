from django.test import TestCase, Client
from mangaki.models import Work, Category, Trope


class ErrorPageTest(TestCase):

    def setUp(self):
        self.client = Client()
        anime = Category.objects.get(slug='anime')
        Work.objects.create(
            title='Initial D',
            source='Fujiwara Bunta',
            category=anime
        )
        Trope.objects.create(
            trope='INERTIA DORIFTU ?!',
            author='Keisuke Takahashi',
            origin=Work.objects.get(title='Initial D')
        )
        self.work = Work.objects.get(title='Initial D')
        self.trope = Trope.objects.get()

    def test_trope(self):
        response = self.client.get('/404/')
        self.assertEqual(response.status_code, 404)
        self.assertIn(self.trope.trope, str(response.content))

    def test_no_trope(self):  # An error 500 could occur in this case.
        self.trope.delete()
        response = self.client.get('/404/')
        self.assertEqual(response.status_code, 404)
