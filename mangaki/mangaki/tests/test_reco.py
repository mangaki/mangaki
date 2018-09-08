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
        self.anime_category = Category.objects.get(slug='anime')
        manga = Category.objects.get(slug='manga')

        works = [
            Work(title='Anime B', nb_episodes=0, category=self.anime_category),
            Work(title='Anime A', nb_episodes=1, category=self.anime_category),
            Work(title='Manga B', category=manga),
            Work(title='Manga A', category=manga),
        ]
        works = Work.objects.bulk_create(works)

        # This will work as long as zero.dataset.RATED_BY_AT_LEAST <= 2
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

    def test_als_reco(self):
        self.client.login(username='test', password='test')
        reco_url = reverse('get-reco-algo-list', args=['als', 'all'])
        with self.settings(PICKLE_DIR=SNAPSHOT_DIR_TEST):
            response = self.client.get(reco_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 3)
        os.remove(os.path.join(SNAPSHOT_DIR_TEST, 'als-20.pickle'))
        os.remove(os.path.join(SNAPSHOT_DIR_TEST, 'ratings-als-20.pickle'))

    def test_knn_reco_with_new_works(self):
        self.client.login(username='test', password='test')
        # They have one rating
        reco_url = reverse('get-reco-algo-list', args=['knn', 'all'])
        with self.settings(PICKLE_DIR=SNAPSHOT_DIR_TEST):
            response = self.client.get(reco_url)  # Create pickle
        # Here comes a new challenger
        work = Work.objects.create(title='New anime', nb_episodes=0, category=self.anime_category)
        rating = Rating.objects.create(user=get_user_model().objects.get(username='test'), work=work, choice='like')
        # They now have two ratings
        with self.settings(PICKLE_DIR=SNAPSHOT_DIR_TEST):
            response = self.client.get(reco_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 3)
        os.remove(os.path.join(SNAPSHOT_DIR_TEST, 'knn-20.pickle'))
        os.remove(os.path.join(SNAPSHOT_DIR_TEST, 'ratings-knn-20.pickle'))
