from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model


class RecoTest(TestCase):

    def setUp(self):
        get_user_model().objects.create_user(username='test', password='test')

    def test_reco(self, **kwargs):
        self.client.login(username='test', password='test')
        reco_url = reverse('get-reco-algo-list', args=['svd', 'all'])
        self.assertEqual(reco_url, '/data/reco/svd/all.json')
