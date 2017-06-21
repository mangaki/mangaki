from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.contrib import admin
from django.db import connection
from mangaki.models import Work, Editor, Category, Studio, WorkCluster, Rating
from datetime import date, timedelta


class MergeTest(TestCase):

    def setUp(self):
        # FIXME: The defaults for editor and studio in Work requires those to
        # exist, or else foreign key constraints fail.
        Editor.objects.create(pk=1)
        Studio.objects.create(pk=1)

        self.user = get_user_model().objects.create_superuser(username='test', password='test', email='steins@gate.co.jp')
        self.users = []
        for username in 'ABCD':
            self.users.append(get_user_model().objects.create_user(username=username, password='test'))

        today = date.today()
        yesterday = date.today() - timedelta(1)
        tomorrow = date.today() + timedelta(1)

        anime = Category.objects.get(slug='anime')
        Work.objects.bulk_create([Work(title='Sangatsu no Lion', category=anime) for _ in range(10)])
        self.work_ids = Work.objects.values_list('id', flat=True)
        # Admin rated every movie
        Rating.objects.bulk_create([Rating(work_id=work_id, user=self.user, choice='like') for work_id in self.work_ids])

        Rating.objects.bulk_create([
            Rating(work_id=self.work_ids[0], user=self.users[0], choice='like', date=today),
            Rating(work_id=self.work_ids[1], user=self.users[0], choice='favorite', date=tomorrow),
            Rating(work_id=self.work_ids[2], user=self.users[0], choice='dislike', date=yesterday),
            Rating(work_id=self.work_ids[1], user=self.users[1], choice='favorite', date=today),
            Rating(work_id=self.work_ids[0], user=self.users[2], choice='favorite', date=today),
            Rating(work_id=self.work_ids[2], user=self.users[2], choice='like', date=yesterday),
            Rating(work_id=self.work_ids[0], user=self.users[3], choice='favorite', date=yesterday)
        ])

    def test_merge(self, **kwargs):
        self.client.login(username='test', password='test')
        merge_url = reverse('admin:mangaki_work_changelist')
        response = self.client.post(merge_url, {'action': 'merge', admin.ACTION_CHECKBOX_NAME: self.work_ids})
        self.assertEqual(response.status_code, 200)

    def test_merge_confirmed(self, **kwargs):
        self.client.login(username='test', password='test')
        merge_url = reverse('admin:mangaki_work_changelist')
        context = {
            'action': 'merge',
            admin.ACTION_CHECKBOX_NAME: self.work_ids,
            'confirm': 1,
            'id': self.work_ids[0],  # Chosen ID for the canonical work
            'fields_to_choose': ''
        }
        with self.assertNumQueries(5):
            self.client.post(merge_url, context)
        self.assertEqual(Work.all_objects.filter(redirect__isnull=True).count(), 1)
        self.assertEqual(WorkCluster.objects.count(), 1)
