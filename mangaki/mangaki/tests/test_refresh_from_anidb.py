# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

import os

import responses
from django.conf import settings
from django.test import TestCase

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.admin import helpers

from mangaki.models import Work, Category
from mangaki.utils.anidb import AniDB, client


class RefreshFromAniDBTest(TestCase):
    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_DATA_DIR, filename), 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def add_to_responses(filename):
        responses.add(
            responses.GET,
            AniDB.BASE_URL,
            body=RefreshFromAniDBTest.read_fixture('anidb/'+filename),
            status=200,
            content_type='application/xml'
        )

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username='test', password='test', email='email@email.email')

        client.client_id = 'fake'
        client.client_ver = 1
        client.is_available = True

        self.anime = Category.objects.get(slug='anime')
        Work.objects.bulk_create([
            Work(title='Hibike! Euphonium', anidb_aid=10889, category=self.anime),
            Work(title='Punchline', category=self.anime),
            Work(title='Kiznaiver', anidb_aid=11692, category=self.anime),
            Work(title='Kiznaiver Duplicate', anidb_aid=11692, category=self.anime)
        ])
        self.work_ids = Work.objects.values_list('pk', flat=True)

    @responses.activate
    def test_refresh_work_from_anidb(self):
        self.add_to_responses('hibike_euphonium.xml')
        self.add_to_responses('punchline.xml')

        self.client.login(username='test', password='test')
        refresh_work_from_anidb_url = reverse('admin:mangaki_work_changelist')
        response = self.client.post(
            refresh_work_from_anidb_url,
            {'action': 'refresh_work_from_anidb', helpers.ACTION_CHECKBOX_NAME: self.work_ids},
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Work.objects.get(anidb_aid=10889).title, 'Hibike! Euphonium')

    @responses.activate
    def test_refresh_tags_from_anidb(self):
        self.add_to_responses('hibike_euphonium.xml')
        self.client.login(username='test', password='test')

        refresh_tags_from_anidb_url = reverse('admin:mangaki_work_changelist')
        response = self.client.post(
            refresh_tags_from_anidb_url,
            {'action': 'update_tags_via_anidb', helpers.ACTION_CHECKBOX_NAME: self.work_ids},
            follow=True
        )
        self.assertEqual(response.status_code, 200)

    @responses.activate
    def test_refresh_tags_from_anidb_confirmed(self):
        self.add_to_responses('hibike_euphonium.xml')
        self.client.login(username='test', password='test')
        hibike = Work.objects.get(title='Hibike! Euphonium')

        refresh_tags_from_anidb_url = reverse('admin:mangaki_work_changelist')
        context = {
            'action': 'update_tags_via_anidb',
            helpers.ACTION_CHECKBOX_NAME: self.work_ids,
            'confirm': 1,
            'to_update_work_ids': [str(hibike.pk)],
            'work_ids': [str(hibike.pk), str(hibike.pk), str(hibike.pk)],
            'tag_titles': ['female protagonist', 'facial distortion', 'training'],
            'weights': ['0', '0', '400'],
            'anidb_tag_ids': ['5851', '4055', '3831'],
            'tag_operations': ['added', 'added', 'added'],
            'tag_checkboxes': [str(hibike.pk)+':5851', str(hibike.pk)+':4055', str(hibike.pk)+':3831']
        }

        response = self.client.post(refresh_tags_from_anidb_url, context)
        self.assertEqual(response.status_code, 302)

        tags = set(Work.objects.get(anidb_aid=10889).taggedwork_set.all().values_list('tag__title', flat=True))
