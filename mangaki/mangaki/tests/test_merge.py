from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.contrib import admin
from mangaki.models import Work, Editor, Category, Studio, WorkCluster


class RecoTest(TestCase):

    def setUp(self):
        # FIXME: The defaults for editor and studio in Work requires those to
        # exist, or else foreign key constraints fail.
        Editor.objects.create(pk=1)
        Studio.objects.create(pk=1)

        self.user = get_user_model().objects.create_superuser(username='test', password='test', email='steins@gate.co.jp')
        anime = Category.objects.get(slug='anime')
        w1 = Work.objects.create(title='coucou', category=anime)
        w2 = Work.objects.create(title='coucou2', category=anime)
        self.work_ids = [w1.id, w2.id]

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
            'id': self.work_ids[0],
            'fields_to_choose': ''
        }
        self.client.post(merge_url, context)
        self.assertEqual(Work.all_objects.filter(redirect__isnull=False).count(), 1)
        self.assertEqual(WorkCluster.objects.count(), 1)
