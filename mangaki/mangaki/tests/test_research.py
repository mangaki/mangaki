from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from mangaki.models import Profile
from mangaki.utils.tokens import compute_token
from django.conf import settings


HASH_NACL_TEST = 'sel'


class ResearchTest(TestCase):

    def setUp(self):
        self.username = 'test'
        self.user = get_user_model().objects.create_user(username=self.username, password='test')
        self.research_url = reverse('research')
        self.bad_token = 'xxx'
        with self.settings(HASH_NACL=HASH_NACL_TEST):
            self.good_token = compute_token(self.username)

    def test_post_research_nok_when_logged(self, **kwargs):
        self.client.login(username=self.username, password='test')
        self.client.post(self.research_url, {'research_ok': 'false'})
        self.assertFalse(Profile.objects.get(user=self.user).research_ok)

    def test_post_research_ok_when_logged(self, **kwargs):
        self.client.login(username=self.username, password='test')
        self.client.post(self.research_url, {'research_ok': 'true'})
        self.assertTrue(Profile.objects.get(user=self.user).research_ok)

    def test_post_research_ok_when_not_logged_bad_token(self, **kwargs):
        self.user.profile.research_ok = False
        self.user.profile.save()
        response = self.client.post(self.research_url, {'yes': 'OK', 'username': self.username, 'token': self.bad_token})
        self.assertEqual(response.status_code, 401)  # Unauthorized
        self.assertFalse(Profile.objects.get(user=self.user).research_ok)

    def test_post_research_ok_when_not_logged_good_token(self, **kwargs):
        self.user.profile.research_ok = False
        self.user.profile.save()
        with self.settings(HASH_NACL=HASH_NACL_TEST):
            response = self.client.post(self.research_url, {'yes': 'OK', 'username': self.username, 'token': self.good_token})
            self.assertEqual(response.status_code, 200)  # Authorized
            self.assertTrue(Profile.objects.get(user=self.user).research_ok)

    def test_get_research_when_not_logged_bad_token(self):
        response = self.client.get(self.research_url, {'username': self.username, 'token': self.bad_token})
        self.assertEqual(response.status_code, 401)  # Unauthorized

    def test_get_research_when_not_logged_good_token(self):
        with self.settings(HASH_NACL=HASH_NACL_TEST):
            response = self.client.get(self.research_url, {'username': self.username, 'token': self.good_token})
            self.assertEqual(response.status_code, 200)
