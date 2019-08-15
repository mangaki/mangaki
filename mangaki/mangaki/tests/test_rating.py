from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from mangaki.models import Studio, Category, Rating, Editor, Work


class RatingTest(TestCase):

    def create_anime(self, **kwargs):
        anime_category = Category.objects.get(slug='anime')
        return Work.objects.create(category=anime_category, **kwargs)

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='test',
                                                         password='test')
        self.anime = self.create_anime(title='Cowboy Bebop')
        # Need another work, otherwise work-list are redirected to work-detail
        self.create_anime(title='Cowboy Bebop: The Movie')

    def test_toggle_rating(self, **kwargs):
        self.client.login(username='test', password='test')
        vote_url = reverse('vote', args=[self.anime.id])

        self.client.post(vote_url, {'choice': 'like'})
        rating = Rating.objects.get(user=self.user, work_id=self.anime.id)
        self.assertEqual(rating.choice, 'like')

        self.client.post(vote_url, {'choice': 'favorite'})
        rating = Rating.objects.get(user=self.user, work_id=self.anime.id)
        self.assertEqual(rating.choice, 'favorite')

        self.client.post(vote_url, {'choice': 'favorite'})  # Cancel my vote
        has_rating = (Rating.objects.filter(user=self.user,
                                            work_id=self.anime.id).exists())
        self.assertFalse(has_rating)

    def test_anonymized_rating(self):
        vote_url = reverse('vote', args=[self.anime.id])
        response = self.client.post(vote_url, {'choice': 'like'})
        self.assertEqual(response.content, b'like')

        profile_url = reverse('my-profile', args=['anime', 'seen'])
        response = self.client.get(profile_url)
        self.assertIn(self.anime.title, response.content.decode('utf-8'))

    def test_rating_display(self):
        self.client.login(username='test', password='test')
        vote_url = reverse('vote', args=[self.anime.id])
        self.client.post(vote_url, {'choice': 'like'})

        # Profile with posters contains rating
        profile_url = reverse('profile-works', args=['test', 'anime', 'seen'])
        response = self.client.get(profile_url)
        self.assertIn('checked', response.content.decode('utf-8'))

        # Profile without posters contains rating
        response = self.client.get(profile_url, {'flat': True})
        self.assertIn('checked', response.content.decode('utf-8'))

        anime_url = reverse('work-detail', args=['anime', self.anime.id])
        # Anime detail contains rating
        response = self.client.get(anime_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('checked', response.content.decode('utf-8'))

        # Anime with posters contains rating
        anime_list_url = reverse('work-list', args=['anime'])
        for sort_mode in {'popularity', 'controversy'}:
            response = self.client.get(anime_list_url, {'sort': sort_mode})
            self.assertEqual(response.status_code, 200)
            self.assertIn('checked', response.content.decode('utf-8'))

        # Popular anime without posters contains rating
        response = self.client.get(anime_list_url, {'sort': 'popularity',
                                                   'flat': True})
        self.assertEqual(response.status_code, 200)
        self.assertIn('checked', response.content.decode('utf-8'))
