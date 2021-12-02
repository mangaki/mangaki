# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

import logging
import json
import os
import shutil

from django.test import TestCase
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model

from mangaki.models import Profile


ML_SNAPSHOT_ROOT_TEST = '/tmp/test_reco/'

def get_path(key):
    return os.path.join(ML_SNAPSHOT_ROOT_TEST, '{:s}'.format(key))


class RecoTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='test', password='test')
        friend = get_user_model().objects.create_user(username='friend', password='test')
        private = get_user_model().objects.create_user(username='private', password='test')
        Profile.objects.filter(user_id=private.id).update(is_shared=False)

    def test_add_url(self, **kwargs):
        self.client.login(username='test', password='test')
        add_url = reverse_lazy('add-friend', args=['friend'])
        self.assertEqual(add_url, '/add_friend/friend')

    def test_del_url(self, **kwargs):
        self.client.login(username='test', password='test')
        del_url = reverse_lazy('del-friend', args=['friend'])
        self.assertEqual(del_url, '/del_friend/friend')

    def test_get_url(self, **kwargs):
        self.client.login(username='test', password='test')
        get_url = reverse_lazy('get-friends')
        self.assertEqual(get_url, '/getfriends.json')

    def test_add_public_friend(self):
        self.client.login(username='test', password='test')
        add_friend_url = reverse_lazy('add-friend', args=['friend'])
        del_friend_url = reverse_lazy('del-friend', args=['friend'])
        friends_url = reverse_lazy('get-friends')
        self.client.post(add_friend_url)
        response = self.client.get(friends_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 1)
        self.client.post(del_friend_url)
        response = self.client.get(friends_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 0)

    def test_add_private_friend(self):
        self.client.login(username='test', password='test')
        add_friend_url = reverse_lazy('add-friend', args=['private'])
        del_friend_url = reverse_lazy('del-friend', args=['private'])
        friends_url = reverse_lazy('get-friends')
        self.client.post(add_friend_url)
        response = self.client.get(friends_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 0)
        self.client.post(del_friend_url)
        response = self.client.get(friends_url)
        self.assertEqual(len(json.loads(response.content.decode('utf-8'))), 0)
