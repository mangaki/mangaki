from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from mangaki.models import Studio, Category, Rating, Editor, Work


class RatingTest(TestCase):

    def create_anime(self, **kwargs):
        anime_category = Category.objects.get(slug='anime')
        return Work.objects.create(category=anime_category, **kwargs)

    def setUp(self):
        # FIXME: The defaults for editor and studio in Work requires those to
        # exist, or else foreign key constraints fail.
        Editor.objects.create(pk=1)
        Studio.objects.create(pk=1)
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
