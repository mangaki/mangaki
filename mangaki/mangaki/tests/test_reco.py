import logging
import json
import os

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

from mangaki.models import Category, Work, Rating


SNAPSHOT_DIR_TEST = '/tmp/test_reco'


class RecoTest(TestCase):

    def setUp(self):
        user = get_user_model().objects.create_user(username='test', password='test')
        otaku = get_user_model().objects.create_user(username='otaku', password='test')
        otaku2 = get_user_model().objects.create_user(username='otaku2', password='test')
        anime = Category.objects.get(slug='anime')
        manga = Category.objects.get(slug='manga')

        works = [
            Work(title='Anime B', nb_episodes=0, category=anime),
            Work(title='Anime A', nb_episodes=1, category=anime),
            Work(title='Manga B', category=manga),
            Work(title='Manga A', category=manga),
        ]
        works = Work.objects.bulk_create(works)

        ratings = ([Rating(user=otaku, work=work, choice='like') for work in works] + 
                   [Rating(user=otaku2, work=work, choice='dislike') for work in works] + 
                   [Rating(user=user, work=works[0], choice='dislike')])
        Rating.objects.bulk_create(ratings)

        if not os.path.exists(SNAPSHOT_DIR_TEST):
            os.makedirs(SNAPSHOT_DIR_TEST)

    def test_reco_url(self, **kwargs):
        self.client.login(username='test', password='test')
        reco_url = reverse('get-reco-algo-list', args=['svd', 'all'])
        self.assertEqual(reco_url, '/data/reco/svd/all.json')

    def test_reco(self):
        self.client.login(username='test', password='test')
        reco_url = reverse('get-reco-algo-list', args=['als', 'all'])
        with self.settings(PICKLE_DIR=SNAPSHOT_DIR_TEST):
            response = self.client.get(reco_url)
        self.assertEqual(len(json.loads(response.content)), 3)
        os.remove(os.path.join(SNAPSHOT_DIR_TEST, 'als-20.pickle'))
        os.remove(os.path.join(SNAPSHOT_DIR_TEST, 'ratings-als-20.pickle'))
