from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.contrib import admin
from django.db import connection
from mangaki.models import Work, Editor, Category, Studio, WorkCluster, Rating, Staff, Role, Artist, Genre, Reference
from datetime import datetime, timedelta


class MergeTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username='test', password='test', email='steins@gate.co.jp')
        self.users = []
        for username in 'ABCD':
            self.users.append(get_user_model().objects.create_user(username=username, password='test'))

        today = datetime.now()
        yesterday = datetime.now() - timedelta(1)
        tomorrow = datetime.now() + timedelta(1)

        anime = Category.objects.get(slug='anime')
        Work.objects.bulk_create([Work(title='Sangatsu no Lion', category=anime) for _ in range(10)])
        self.work_ids = Work.objects.values_list('id', flat=True)
        # Admin rated every movie
        Rating.objects.bulk_create([Rating(work_id=work_id, user=self.user, choice='like') for work_id in self.work_ids])

        the_artist = Artist.objects.create(name='Yoko Kanno')

        references = []
        for work_id in self.work_ids:
            references.extend(Reference.objects.bulk_create([
                Reference(work_id=work_id, source='MAL', identifier=31646,
                          url='https://myanimelist.net/anime/31646'),
                Reference(work_id=work_id, source='AniDB', identifier=11606,
                          url='https://anidb.net/perl-bin/animedb.pl?show=anime&aid=11606')
            ]))

        roles = Role.objects.bulk_create([
            Role(name='Director', slug='xxx'),
            Role(name='Composer', slug='yyy')
        ])

        Staff.objects.bulk_create([
            Staff(work_id=self.work_ids[0], artist=the_artist, role=roles[0]),
            Staff(work_id=self.work_ids[1], artist=the_artist, role=roles[0]),
            Staff(work_id=self.work_ids[1], artist=the_artist, role=roles[1])
        ])

        genres = Genre.objects.bulk_create([
            Genre(title='SF'),
            Genre(title='Slice of life')
        ])
        Work.objects.get(id=self.work_ids[0]).genre.add(genres[0])
        Work.objects.get(id=self.work_ids[1]).genre.add(genres[0])
        Work.objects.get(id=self.work_ids[1]).genre.add(genres[1])

        # Rating are built so that after merge, only the favorites should be kept
        Rating.objects.bulk_create([
            Rating(work_id=self.work_ids[0], user=self.users[0], choice='like', date=today),
            Rating(work_id=self.work_ids[1], user=self.users[0], choice='favorite', date=tomorrow),
            Rating(work_id=self.work_ids[2], user=self.users[0], choice='dislike', date=yesterday),
            Rating(work_id=self.work_ids[1], user=self.users[1], choice='favorite', date=today),
            Rating(work_id=self.work_ids[0], user=self.users[2], choice='favorite', date=today),
            Rating(work_id=self.work_ids[2], user=self.users[2], choice='like', date=yesterday),
            Rating(work_id=self.work_ids[0], user=self.users[3], choice='favorite', date=yesterday)
        ])
        Rating.objects.filter(work_id=self.work_ids[1], user=self.users[0]).update(date=tomorrow)
        Rating.objects.filter(work_id=self.work_ids[2], user=self.users[0]).update(date=yesterday)
        Rating.objects.filter(work_id=self.work_ids[2], user=self.users[2]).update(date=yesterday),
        Rating.objects.filter(work_id=self.work_ids[0], user=self.users[3]).update(date=yesterday)

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
            'fields_to_choose': '',
            'fields_required': ''
        }
        with self.assertNumQueries(36):
            self.client.post(merge_url, context)
        self.assertEqual(list(Rating.objects.filter(user__in=self.users).values_list('choice', flat=True)), ['favorite'] * 4)
        self.assertEqual(Work.all_objects.filter(redirect__isnull=True).count(), 1)
        self.assertEqual(WorkCluster.objects.count(), 1)
        self.assertEqual(Staff.objects.count(), 2)
        self.assertEqual(Work.objects.get(id=self.work_ids[0]).genre.count(), 2)
