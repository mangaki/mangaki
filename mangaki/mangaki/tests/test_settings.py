from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from mangaki.models import Profile
from mangaki.utils.tokens import compute_token, NEWS_SALT
from django.conf import settings


class SettingsTest(TestCase):

    def setUp(self):
        self.username = 'test'
        self.user = get_user_model().objects.create_user(
            username=self.username, password='test')
        self.settings_url = reverse('settings')
        self.bad_token = 'xxx'
        self.good_token = compute_token(NEWS_SALT, self.username)

    def test_post_settings_ok_when_not_logged_bad_token(self, **kwargs):
        self.user.profile.newsletter_ok = False
        self.user.profile.save()
        response = self.client.post(self.settings_url,
            {'yes': 'OK', 'username': self.username, 'token': self.bad_token})
        self.assertEqual(response.status_code, 401)  # Unauthorized
        self.assertFalse(Profile.objects.get(user=self.user).newsletter_ok)

    def test_post_settings_ok_when_not_logged_good_token(self, **kwargs):
        self.user.profile.newsletter_ok = False
        self.user.profile.save()
        response = self.client.post(self.settings_url,
            {'yes': 'OK', 'username': self.username, 'token': self.good_token})
        self.assertEqual(response.status_code, 200)  # Authorized
        self.assertTrue(Profile.objects.get(user=self.user).newsletter_ok)

    def test_get_settings_when_not_logged_bad_token(self):
        response = self.client.get(self.settings_url,
            {'username': self.username, 'token': self.bad_token})
        self.assertEqual(response.status_code, 401)  # Unauthorized

    def test_get_settings_when_not_logged_good_token(self):
        response = self.client.get(self.settings_url,
            {'username': self.username, 'token': self.good_token})
        self.assertEqual(response.status_code, 200)
