# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError
from django.test import TestCase

from mangaki.factories import create_user_with_profile
from mangaki.models import Category, Editor, Studio, Work


class WorkTest(TestCase):

    def create_anime(self, **kwargs):
        anime = Category.objects.get(slug='anime')
        return Work.objects.create(category=anime, **kwargs)

    def create_manga(self, **kwargs):
        manga = Category.objects.get(slug='manga')
        return Work.objects.create(category=manga, **kwargs)

    def create_album(self, **kwargs):
        album = Category.objects.get(slug='album')
        return Work.objects.create(category=album, **kwargs)

    def setUp(self):
        self.anime = self.create_anime(title='STEINS;GATE',
            source='Ryan',
            ext_poster='ryan.png',
            nb_episodes=26, # + 1 with the alternate beta episode.
            anime_type='Seinen'
        )

        self.nsfw_anime = self.create_anime(title='Dakara boku ga H wa dekinai.',
            source='Not Ryan',
            ext_poster='dakara.png',
            nsfw=True,
            nb_episodes=24, # unsure, but we don't care.
            anime_type='Ecchi-Hentai'
        )


        self.manga = self.create_manga(title='Medaka Box',
            source='Ryan',
            ext_poster='zenkichi.png',
            manga_type='Shonen'
        )

        self.album = self.create_album(title='Bungou Stray Dogs Original Soundtrack',
            source='Ryan',
            ext_poster='atsuchi_and_dazai.png',
            vgmdb_aid=58065
        )

        self.fake_user = create_user_with_profile(username='Raito_Bezarius', profile={
            'nsfw_ok': False
        })

        self.fake_user_with_nsfw = create_user_with_profile(username='Raito_Bezarius_NSFW', profile={
            'nsfw_ok': True
        })

    def test_search(self):
        accents = self.create_anime(title='Un titre accentué oui oui')
        no_accents = self.create_anime(title='Un titre sans accents non non')
        tests = [
            ('medaka', self.manga),
            ('titre', [accents, no_accents]),
            ('titre oui', accents),
            ('titre non', no_accents),
            ('accentue', accents),
            ('accent', [accents, no_accents]),
            ('boxers', None),
        ]
        for query, expected in tests:
            qs = list(Work.objects.search(query))
            if expected is None:
                self.assertFalse(qs)
                continue
            elif isinstance(expected, (list, tuple)):
                self.assertEqual(len(qs), len(expected))
                for w in qs:
                    self.assertIn(w, expected)
                for e in expected:
                    self.assertIn(e, qs)
            else:
                self.assertEqual(len(qs), 1)
                self.assertEqual(qs[0], expected)

    def test_anime_creation(self):
        w = self.anime

        self.assertIsInstance(w, Work)
        self.assertEqual(w.get_absolute_url(), '/anime/{}'.format(w.id))
        self.assertEqual(w.category.slug, 'anime')

    def test_manga_creation(self):
        w = self.manga

        self.assertIsInstance(w, Work)
        self.assertEqual(w.get_absolute_url(), '/manga/{}'.format(w.id))
        self.assertEqual(w.category.slug, 'manga')

    def test_album_creation(self):
        w = self.album

        self.assertIsInstance(w, Work)
        self.assertEqual(w.get_absolute_url(), '/album/{}'.format(w.id))
        self.assertEqual(w.category.slug, 'album')

    def test_work_creation(self):
        """
        Work cannot be created without a category, the `Work.save` method will throw an IntegrityError.
        """

        with self.assertRaises(IntegrityError):
            Work.objects.create(title='a cool work')

    def test_work_safe_poster_for_non_nsfw(self):
        w = self.anime

        self.assertNotIn('nsfw', w.safe_poster(AnonymousUser()))
        self.assertNotIn('nsfw', w.safe_poster(self.fake_user))
        self.assertNotIn('nsfw', w.safe_poster(self.fake_user_with_nsfw))

    def test_work_safe_poster_for_nsfw(self):
        w = self.nsfw_anime

        self.assertIn('nsfw', w.safe_poster(AnonymousUser()))
        self.assertIn('nsfw', w.safe_poster(self.fake_user))
        self.assertNotIn('nsfw', w.safe_poster(self.fake_user_with_nsfw))

    def test_work_group_by_category(self):
        grouped = Work.objects.group_by_category()
        self.assertIsInstance(grouped, dict)
        pks = []
        for category_id, works in grouped.items():
            self.assertNotEqual(len(works), 0)
            for work in works:
                self.assertEqual(work.category_id, category_id)
                pks.append(work.pk)

        self.assertEqual(len(set(pks)), len(pks))
        self.assertEqual(set(pks), set(Work.objects.values_list('id', flat=True)))

    def test_work_group_by_category_order(self):
        anime = Category.objects.get(slug='anime')
        manga = Category.objects.get(slug='manga')

        works = [
            Work(title='Anime B', nb_episodes=0, category=anime),
            Work(title='Anime A', nb_episodes=1, category=anime),
            Work(title='Manga B', category=manga),
            Work(title='Manga A', category=manga),
        ]
        works = Work.objects.bulk_create(works)
        works = [work.pk for work in works]

        grouped = Work.objects.filter(pk__in=works).order_by('pk').group_by_category()
        self.assertEqual(len(grouped), 2)
        self.assertEqual(len(grouped[anime.id]), 2)
        self.assertEqual(len(grouped[manga.id]), 2)

        self.assertEqual([work.title for work in grouped[anime.id]], ['Anime B', 'Anime A'])
        self.assertEqual([work.title for work in grouped[manga.id]], ['Manga B', 'Manga A'])
       
        grouped = Work.objects.filter(pk__in=works).order_by('title').group_by_category()
        self.assertEqual(len(grouped), 2)
        self.assertEqual(len(grouped[anime.id]), 2)
        self.assertEqual(len(grouped[manga.id]), 2)

        self.assertEqual([work.title for work in grouped[anime.id]], ['Anime A', 'Anime B'])
        self.assertEqual([work.title for work in grouped[manga.id]], ['Manga A', 'Manga B'])
