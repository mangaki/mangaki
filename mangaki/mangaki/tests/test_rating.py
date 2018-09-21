from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

from mangaki.models import Studio, Category, Rating, Editor, Work


class RatingTest(TestCase):

    def create_anime(self, **kwargs):
        anime_category = Category.objects.get(slug='anime')
        return Work.objects.create(category=anime_category, **kwargs)

    def setUp(self):
        get_user_model().objects.create_user(username='test', password='test')
        self.anime = self.create_anime(title='La Mélancolie de Haruhi Suzumiya')

    def test_rating(self, **kwargs):
        self.client.login(username='test', password='test')
        vote_url = reverse('vote', args=[self.anime.id])
        self.client.post(vote_url, {'choice': 'like'})
        self.assertEqual(Rating.objects.get(user__username='test', work_id=self.anime.id).choice, 'like')
        self.client.post(vote_url, {'choice': 'favorite'})
        self.assertEqual(Rating.objects.get(user__username='test', work_id=self.anime.id).choice, 'favorite')
        self.client.post(vote_url, {'choice': 'favorite'})  # Cancel my vote
        self.assertFalse(Rating.objects.filter(user__username='test', work_id=self.anime.id).exists())

    def test_anonymized_rating(self):
        vote_url = reverse('vote', args=[self.anime.id])
        response = self.client.post(vote_url, {'choice': 'like'})
        self.assertEqual(response.content, b'like')

        profile_url = reverse('my-profile', args=['anime', 'seen'])
        response = self.client.get(profile_url)
        self.assertIn(self.anime.title, response.content.decode('utf-8'))
