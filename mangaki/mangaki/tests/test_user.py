# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from django.test import TestCase
from django.contrib.auth import get_user_model

from mangaki.models import Profile


class UserTest(TestCase):  
    def setUp(self):
        self.User = get_user_model()

    def test_user_creation_creates_profile(self):
        u = self.User.objects.create_user('testuser')
        self.assertIsInstance(u.profile, Profile)
