import json
import time

from django.contrib.auth import get_user_model
from django.db.models import Max
from django.test import Client, TestCase

from mangaki.models import Category, Editor, Studio, Work, Suggestion, Evidence


class WorkFactoryMixin:
    def setUp(self):
        self.User = get_user_model()
        self.client = Client()

        anime = Category.objects.get(slug='anime')

        self.anime = Work.objects.create(
            title='Title',
            category=anime)


class AuthenticatedMixin:
    def setUp(self):
        super().setUp()
        self.user = self.User.objects.create_user('username')
        self.client.force_login(self.user)


class SuggestionFactoryMixin:
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='test', password='test')
        self.client = Client()

        self.anime = Work.objects.create(
            title='Title',
            category=Category.objects.get(slug='anime')
        )

        self.suggestion = Suggestion.objects.create(
            user=self.user,
            work=self.anime,
            message='Message'
        )

        self.evidence = Evidence.objects.create(
            user=self.user,
            suggestion=self.suggestion
        )


class WorkDetailAnonymousTest(WorkFactoryMixin, TestCase):
    def get_invalid_pk(self, model):
        pk = model.objects.aggregate(Max('pk'))['pk__max'] + 10
        self.assertFalse(model.objects.filter(pk=pk).exists())
        return pk

    def test_work_detail(self):
        response = self.client.get('/anime/{:d}'.format(self.anime.pk))
        self.assertEqual(response.status_code, 200)  # 200 OK

        self.assertEqual(response.context['object'], self.anime)
        self.assertNotIn('suggestion_form', response.context)

    def test_work_detail_redirect(self):
        response = self.client.get('/work/{:d}'.format(self.anime.pk))
        self.assertEqual(response.status_code, 301)  # 301 Moved Permanently
        self.assertEqual(response.url, '/anime/{:d}'.format(self.anime.pk))

    def test_work_detail_trailing_slash(self):
        response = self.client.get('/anime/{:d}/'.format(self.anime.pk))
        self.assertEqual(response.status_code, 404)  # 404 Not Found

    def test_work_detail_nonexistent(self):
        invalid_pk = self.get_invalid_pk(Work)

        response = self.client.get('/anime/{:d}'.format(invalid_pk))
        self.assertEqual(response.status_code, 404)  # 404 Not Found

        response = self.client.get('/work/{:d}'.format(invalid_pk))
        self.assertEqual(response.status_code, 404)  # 404 Not Found

        response = self.client.post('/anime/{:d}'.format(invalid_pk))
        self.assertEqual(response.status_code, 404)  # 404 Not Found

    def test_work_post_forbidden(self):
        response = self.client.post('/anime/{:d}'.format(self.anime.pk))
        self.assertEqual(response.status_code, 403)  # 403 Forbidden


class WorkDetailAuthenticatedTest(AuthenticatedMixin, WorkFactoryMixin, TestCase):
    def test_work_detail_auth(self):
        response = self.client.get('/anime/{:d}'.format(self.anime.pk))
        self.assertEqual(response.status_code, 200)  # 200 OK

        self.assertEqual(response.context['object'], self.anime)
        self.assertIn('suggestion_form', response.context)

    def test_work_detail_post_auth(self):
        self.assertFalse(self.user.suggestion_set.exists())
        response = self.client.post('/anime/{:d}'.format(self.anime.pk), {
            'work': self.anime.pk,
            'problem': 'title',
            'message': "Mauvais titre",
        })
        self.assertEqual(response.status_code, 302)  # 302 Found
        self.assertEqual(response.url, '/anime/{:d}'.format(self.anime.pk))

        suggestions = list(self.user.suggestion_set.all())
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].problem, 'title')
        self.assertEqual(suggestions[0].message, "Mauvais titre")
        self.assertEqual(suggestions[0].work, self.anime)

    def test_work_detail_post_no_message(self):
        self.assertFalse(self.user.suggestion_set.exists())
        response = self.client.post('/anime/{:d}'.format(self.anime.pk), {
            'work': self.anime.pk,
            'problem': 'title',
        })
        self.assertEqual(response.status_code, 302)  # 302 Found
        self.assertEqual(response.url, '/anime/{:d}'.format(self.anime.pk))

        suggestions = list(self.user.suggestion_set.all())
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].problem, 'title')
        self.assertEqual(suggestions[0].message, "")
        self.assertEqual(suggestions[0].work, self.anime)

    def test_work_detail_post_invalid(self):
        response = self.client.post('/anime/{:d}'.format(self.anime.pk), {
            'work': self.anime.pk,
            'problem': 'glougoug',
            'message': "Mauvais titre",
        })
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/anime/{:d}'.format(self.anime.pk), {
            'work': self.anime.pk,
            'message': "Mauvais titre",
        })
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/anime/{:d}'.format(self.anime.pk), {
            'problem': 'title',
            'message': "Mauvais titre",
        })
        self.assertEqual(response.status_code, 200)


class AnonymousViewsTest(WorkFactoryMixin, TestCase):
    def test_get_work(self):
        response = self.client.get('/data/anime.json')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content.decode())
        self.assertEqual(Work.objects.count(), 1)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.anime.pk)

    def test_get_card(self):
        with self.subTest('Popularity slot sort'):
            response = self.client.get('/api/cards/anime/popularity')
            self.assertEqual(response.status_code, 200)

        with self.subTest('Controversy slot sort'):
            response = self.client.get('/api/cards/anime/controversy')
            self.assertEqual(response.status_code, 200)

        with self.subTest('Top slot sort'):
            response = self.client.get('/api/cards/anime/top')
            self.assertEqual(response.status_code, 200)

        with self.subTest('Random slot sort'):
            response = self.client.get('/api/cards/anime/random')
            self.assertEqual(response.status_code, 200)

        # 4 requests have been previously sent.
        with self.subTest('Rate limit'):
            response = self.client.get('/api/cards/anime/black_magic')
            self.assertEqual(response.status_code, 429)

        # Let's recover.
        time.sleep(1)

        with self.subTest('Inexistent slot sort'):
            response = self.client.get('/api/cards/anime/!!!!!')
            self.assertEqual(response.status_code, 404)

    def _test_static_view(self, url):
        response = self.client.get('/{:s}'.format(url))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, '/{:s}/'.format(url))

        response = self.client.get('/{:s}/'.format(url))
        self.assertEqual(response.status_code, 200)

    def test_misc_views(self):
        self._test_static_view('about')
        self._test_static_view('faq')

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_profile_exists(self):
        self.assertFalse(self.User.objects.filter(username='dummy').exists())

        response = self.client.get('/u/dummy')
        self.assertEqual(response.status_code, 404)

        target = self.User.objects.create_user('dummy')
        response = self.client.get('/u/dummy')
        self.assertEqual(response.status_code, 301)

        response = self.client.get('/u/dummy/anime/seen')
        self.assertEqual(response.status_code, 200)


class SuggestionViewsTest(SuggestionFactoryMixin, TestCase):
    def get_invalid_pk(self, model):
        pk = model.objects.aggregate(Max('pk'))['pk__max'] + 10
        self.assertFalse(model.objects.filter(pk=pk).exists())
        return pk

    def test_misc_views(self):
        self._test_static_view('fix')
        self._test_static_view('fix/suggestion')

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def _test_static_view(self, url):
        response = self.client.get('/{:s}'.format(url))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, '/{:s}/'.format(url))

        response = self.client.get('/{:s}/'.format(url))
        self.assertEqual(response.status_code, 200)

    def test_suggestion_view(self):
        with self.subTest('Existing suggestion'):
            response = self.client.get('/fix/suggestion/{:d}'.format(self.suggestion.pk))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['suggestion'], self.suggestion)

        with self.subTest('Non existing suggestion'):
            invalid_pk = self.get_invalid_pk(Suggestion)
            response = self.client.get('/fix/suggestion/{:d}'.format(invalid_pk))
            self.assertEqual(response.status_code, 404)

    def test_update_evidence(self):
        self.client.force_login(self.user)

        response = self.client.post('/evidence/', {
            'agrees': 'on',
            'suggestion': self.suggestion.pk
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/fix/suggestion/{:d}'.format(self.suggestion.pk))

        evidence_updated = Evidence.objects.get(user=self.user, suggestion=self.suggestion)
        self.assertTrue(evidence_updated.agrees)
        self.assertFalse(evidence_updated.needs_help)
