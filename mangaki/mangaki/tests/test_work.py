from django.test import TestCase
from mangaki.models import Work, Anime, Manga, Album
from django.contrib.auth.models import User, AnonymousUser

from mangaki.factories import create_user_with_profile

class WorkTest(TestCase):

    def create_anime(self, **kwargs):
        return Anime.objects.create(**kwargs)

    def create_manga(self, **kwargs):
        return Manga.objects.create(**kwargs)

    def create_album(self, **kwargs):
        return Album.objects.create(**kwargs)

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

        self.fake_user_with_nsfw = create_user_with_profile(username='Raito_Bezarius', profile={
            'nsfw_ok': True
        })


    def test_anime_creation(self):
        w = self.anime

        self.assertIsInstance(w, Anime)
        self.assertEqual(w.get_absolute_url(), '/anime/{}'.format(w.id))
        self.assertEqual(str(w.category), 'Anime')
        self.assertEqual(w.category.slug, 'anime')
        self.assertEqual(str(w), '[{}] {}'.format(w.id, w.title))

    def test_manga_creation(self):
        w = self.manga

        self.assertIsInstance(w, Manga)
        self.assertEqual(w.get_absolute_url(), '/manga/{}'.format(w.id))
        self.assertEqual(str(w.category), 'Manga')
        self.assertEqual(w.category.slug, 'manga')
        self.assertEqual(str(w), w.title) # This seems incoherent with animes. Why special __str__ only for Anime subclasses?

    def test_album_creation(self):
        w = self.album

        self.assertIsInstance(w, Album)
        self.assertEqual(w.get_absolute_url(), '/album/{}'.format(w.id))
        self.assertEqual(str(w.category), 'Album')
        self.assertEqual(w.category.slug, 'album')
        self.assertEqual(str(w), '[{}] {}'.format(w.id, w.title))

    def test_work_creation(self):
        """
        You cannot create a work without a category, the Work.save function will throw:
        TypeError('Unexpected subclass of work: {}'.format(type(self))
        """

        with self.assertRaises(TypeError):
            Work.objects.create(title='a cool work')

    def test_work_safe_poster(self):
        w = Anime.objects.get(title__iexact='STEINS;GATE')
        nsfw_work = Anime.objects.get(anime_type__iexact='Ecchi-Hentai')

        fake_user = create_user(username='Raito_Bezarius')

        self.assertIn('ryan.png', w.safe_poster(AnonymousUser()))
        self.assertIn('ryan.png', w.safe_poster(fake_user))

        fake_user.profile.nsfw_ok = True
        self.assertIn('ryan.png', w.safe_poster(fake_user))
        fake_user.profile.nsfw_ok = False

        self.assertIn('nsfw', nsfw_work.safe_poster(AnonymousUser()))
        self.assertIn('nsfw', nsfw_work.safe_poster(fake_user))

        fake_user.profile.nsfw_ok = True
        self.assertIn('dakara.png', nsfw_work.safe_poster(fake_user))
        fake_user.profile.nsfw_ok = False
