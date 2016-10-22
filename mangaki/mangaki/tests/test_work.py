from django.test import TestCase
from mangaki.models import Work, Category
from django.contrib.auth.models import User, AnonymousUser

from mangaki.factories import create_user_with_profile

class WorkTest(TestCase):

    def create_anime(self, **kwargs):
        anime = Category.objects.get(slug='anime')
        return Work.objects.create(**kwargs, category=anime)

    def create_manga(self, **kwargs):
        manga = Category.objects.get(slug='manga')
        return Work.objects.create(**kwargs, category=manga)

    def create_album(self, **kwargs):
        album = Category.objects.get(slug='album')
        return Work.objects.create(**kwargs, category=album)

    def setUp(self):
        self.anime = self.create_anime(title='STEINS;GATE',
            source='Ryan',
            poster='ryan.png',
            nb_episodes=26, # + 1 with the alternate beta episode.
            anime_type='Seinen'
        )

        self.nsfw_anime = self.create_anime(title='Dakara boku ga H wa dekinai.',
            source='Not Ryan',
            poster='dakara.png',
            nsfw=True,
            nb_episodes=24, # unsure, but we don't care.
            anime_type='Ecchi-Hentai'
        )


        self.manga = self.create_manga(title='Medaka Box',
            source='Ryan',
            poster='zenkichi.png',
            manga_type='Shonen'
        )

        self.album = self.create_album(title='Bungou Stray Dogs Original Soundtrack',
            source='Ryan',
            poster='atsuchi_and_dazai.png',
            vgmdb_aid=58065
        )

        self.fake_user = create_user_with_profile(username='Raito_Bezarius', profile={
            'nsfw_ok': False
        })

        self.fake_user_with_nsfw = create_user_with_profile(username='Raito_Bezarius_NSFW', profile={
            'nsfw_ok': True
        })


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
        Work cannot be created without a category, the `Work.save` method will throw a TypeError.
        """

        with self.assertRaises(TypeError):
            Work.objects.create(title='a cool work')

    def test_work_safe_poster_for_non_nsfw(self):
        w = self.anime

        self.assertIn(w.poster, w.safe_poster(AnonymousUser()))
        self.assertIn(w.poster, w.safe_poster(self.fake_user))
        self.assertIn(w.poster, w.safe_poster(self.fake_user_with_nsfw))

    def test_work_safe_poster_for_nsfw(self):
        w = self.nsfw_anime

        self.assertIn('nsfw', w.safe_poster(AnonymousUser()))
        self.assertIn('nsfw', w.safe_poster(self.fake_user))
        self.assertIn('dakara.png', w.safe_poster(self.fake_user_with_nsfw))
