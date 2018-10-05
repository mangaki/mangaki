from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib import admin
from mangaki.models import Work, Category, WorkTitle, Editor, Studio


class ChangeDefaultTitleTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username='test', password='test', email='email@email.email')

        anime = Category.objects.get(slug='anime')
        Work.objects.bulk_create([
            Work(title='Sangatsu no Lion', category=anime),
            Work(title='Hibike! Euphonium', category=anime),
            Work(title='Kiznaiver', category=anime)
        ])
        self.work_ids = Work.objects.values_list('pk', flat=True)

        WorkTitle.objects.bulk_create([
            WorkTitle(work=Work.objects.get(id=self.work_ids[0]), title='3-gatsu no Lion', type='synonym'),
            WorkTitle(work=Work.objects.get(id=self.work_ids[1]), title='Sound! Euphonium', type='synonym')
        ])
        self.worktitle_ids = WorkTitle.objects.values_list('pk', flat=True)

    def test_change_title(self):
        self.client.login(username='test', password='test')
        change_title_url = reverse('admin:mangaki_work_changelist')
        response = self.client.post(
            change_title_url,
            {'action': 'change_title', admin.ACTION_CHECKBOX_NAME: self.work_ids},
            follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_change_title_no_alternative_titles(self):
        self.client.login(username='test', password='test')
        change_title_url = reverse('admin:mangaki_work_changelist')
        response = self.client.post(
            change_title_url,
            {'action': 'change_title', admin.ACTION_CHECKBOX_NAME: self.work_ids[2]},
            follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_change_title_confirmed(self):
        self.client.login(username='test', password='test')
        change_title_url = reverse('admin:mangaki_work_changelist')
        context = {
            'action': 'change_title',
            admin.ACTION_CHECKBOX_NAME: self.work_ids,
            'confirm': 1,
            'work_ids': self.work_ids,
            'title_ids': self.worktitle_ids
        }

        self.client.post(change_title_url, context)

        self.assertTrue(Work.objects.filter(title='3-gatsu no Lion').exists())
        self.assertTrue(Work.objects.filter(title='Sound! Euphonium').exists())
