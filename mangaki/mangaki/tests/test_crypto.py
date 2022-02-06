# SPDX-FileCopyrightText: 2022, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from django.test import TestCase
from mangaki.utils.crypto import HomomorphicEncryption


class CryptoTest(TestCase):

    def setUp(self):
        self.he = HomomorphicEncryption(['Alice', 'Bob', 'Charles'])

    def test_encryption(self, **kwargs):
        user_parameters = [
            ('Alice', (2, [2, 2])),
            ('Bob', (1, [1, -1])),
            ('Charles', (1, [2, 1])),    
        ]
        encrypted = []
        for user_id, parameters in user_parameters:
            encrypted.append(self.he.encrypt_embeddings(user_id, parameters))
        mean, feat = self.he.decrypt_embeddings(encrypted)
        self.assertEqual(mean, 4)
        self.assertEqual(feat, [5, 2])
