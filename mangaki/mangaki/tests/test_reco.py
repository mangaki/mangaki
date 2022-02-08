# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

import logging
import json
import os
import shutil

from django.test import TestCase
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model

from mangaki.models import Category, Work, Rating
import time


ML_SNAPSHOT_ROOT_TEST = '/tmp/test_reco/'

def get_path(key):
    return os.path.join(ML_SNAPSHOT_ROOT_TEST, '{:s}'.format(key))


class RecoTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='test', password='test')
        friend = get_user_model().objects.create_user(username='friend', password='test')
        otaku = get_user_model().objects.create_user(username='otaku', password='test')
        users = get_user_model().objects.bulk_create([
            get_user_model()(username=f'otaku{i}', password='test') for i in range(20)
        ])
        self.anime_category = Category.objects.get(slug='anime')
        manga = Category.objects.get(slug='manga')

        self.user.profile.friends.add(friend)

        works = [
            Work(title='Anime B', nb_episodes=0, category=self.anime_category),
            Work(title='Anime A', nb_episodes=1, category=self.anime_category),
            Work(title='Manga B', category=manga),
            Work(title='Manga A', category=manga),
        ]
        for _ in range(20):
            works.append(Work(title='Remplissage', category=manga))
        works = Work.objects.bulk_create(works)
        self.work = works[0]

        # This will work as long as zero.dataset.RATED_BY_AT_LEAST <= 2
        ratings = ([Rating(user=otaku, work=work, choice='like') for work in works[2:]] + 
                   [Rating(user=users[2], work=work, choice='dislike') for work in works[2:]] +
                   [Rating(user=friend, work=work, choice='like') for work in works[:2]] +
                   [Rating(user=self.user, work=works[0], choice='dislike')])
        for user in users:
            ratings.append(Rating(user=user, work=works[1], choice='like'))
        Rating.objects.bulk_create(ratings)

        if not os.path.exists(ML_SNAPSHOT_ROOT_TEST):
            os.makedirs(ML_SNAPSHOT_ROOT_TEST)
            for key in {'svd', 'als', 'knn', 'knn-anonymous'}:
                path = get_path(key)
                if not os.path.exists(path):
                    os.makedirs(path)

    def test_reco_url(self, **kwargs):
        self.client.login(username='test', password='test')
        reco_url = reverse_lazy('reco')
        response = self.client.get(reco_url)

    def test_svd_reco_url(self, **kwargs):
        self.client.login(username='test', password='test')
        reco_url = reverse_lazy('get-reco-algo-list', args=['svd', 'all'])
        self.assertEqual(reco_url, '/data/reco/svd/all.json')

    def test_svd_group_reco_url(self, **kwargs):
        self.client.login(username='test', password='test')
        reco_url = reverse_lazy('get-reco-algo-list', args=['svd', 'union', 'all'])
        self.assertEqual(reco_url, '/data/reco/svd/union/all.json')

    def test_als_reco(self):
        self.client.login(username='test', password='test')
        reco_url = reverse_lazy('get-reco-algo-list', args=['als', 'all'])
        with self.settings(ML_SNAPSHOT_ROOT=get_path('als')):
            response = self.client.get(reco_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 8)
        os.remove(os.path.join(get_path('als'), 'svd-20.pickle'))

    def test_group_reco_custom_embed(self):
        self.client.login(username='test', password='test')
        reco_url = reverse_lazy('get-reco-algo-list', args=['knn', 'all'])
        with self.settings(ML_SNAPSHOT_ROOT=get_path('als')):
            response = self.client.get(reco_url)
        friend2 = get_user_model().objects.create_user(username='friend2',
                                                       password='test')
        ratings = [Rating(user=friend2, work=self.work, choice='like')]
        Rating.objects.bulk_create(ratings)
        add_friend_url = reverse_lazy('add-friend', args=['friend2'])
        response = self.client.post(add_friend_url)
        toggle_friend_url = reverse_lazy('toggle-friend', args=['friend2'])
        response = self.client.post(toggle_friend_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 2)
        with self.settings(ML_SNAPSHOT_ROOT=get_path('als')):
            response = self.client.get(reco_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 9)
        os.remove(os.path.join(get_path('als'), 'svd-20.pickle'))

    def test_group_reco_intersection(self):
        self.client.login(username='test', password='test')
        toggle_friend_url = reverse_lazy('toggle-friend', args=['friend'])
        response = self.client.post(toggle_friend_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 2)
        reco_url = reverse_lazy('get-reco-algo-list', args=['als', 'intersection', 'anime'])
        with self.settings(ML_SNAPSHOT_ROOT=get_path('als')):
            response = self.client.get(reco_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 1)
        os.remove(os.path.join(get_path('als'), 'svd-20.pickle'))

    def test_group_reco_union(self):
        self.client.login(username='test', password='test')
        toggle_friend_url = reverse_lazy('toggle-friend', args=['friend'])
        response = self.client.post(toggle_friend_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 2)
        reco_url = reverse_lazy('get-reco-algo-list', args=['als', 'union', 'all'])
        with self.settings(ML_SNAPSHOT_ROOT=get_path('als')):
            response = self.client.get(reco_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 9)
        os.remove(os.path.join(get_path('als'), 'svd-20.pickle'))

    def test_svd_reco_with_new_works(self):
        self.client.login(username='test', password='test')
        # They should have one rating
        self.assertEqual(self.user.rating_set.count(), 1)

        reco_url = reverse_lazy('get-reco-algo-list', args=['svd', 'all'])
        with self.settings(ML_SNAPSHOT_ROOT=get_path('svd')):
            response = self.client.get(reco_url)  # Create pickle

        # Here comes a new challenger
        work = Work.objects.create(title='New anime', nb_episodes=0, category=self.anime_category)
        rating = Rating.objects.create(user=get_user_model().objects.get(username='test'), work=work, choice='like')
        # They now have two ratings
        self.assertEqual(self.user.rating_set.count(), 2)

        with self.settings(ML_SNAPSHOT_ROOT=get_path('svd')):
            response = self.client.get(reco_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 8)
        os.remove(os.path.join(get_path('svd'), 'svd-20.pickle'))

    def test_anonymous_reco(self):
        vote_url = reverse_lazy('vote', args=[self.work.id])
        response = self.client.post(vote_url, {'choice': 'like'})

        reco_url = reverse_lazy('get-reco-algo-list', args=['als', 'anime'])
        with self.settings(ML_SNAPSHOT_ROOT=get_path('knn-anonymous')):
            response = self.client.get(reco_url)  # Create pickle

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 1)

        reco_url = reverse_lazy('get-reco-algo-list', args=['als', 'all'])
        with self.settings(ML_SNAPSHOT_ROOT=get_path('knn-anonymous')):
            response = self.client.get(reco_url)  # Create pickle

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 8)
        os.remove(os.path.join(get_path('knn-anonymous'), 'svd-20.pickle'))

    def tearDown(self):
        shutil.rmtree(ML_SNAPSHOT_ROOT_TEST)
