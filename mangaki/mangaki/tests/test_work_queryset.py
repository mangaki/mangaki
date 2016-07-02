from django.test import TestCase
from django.db.models import F, Value
from mangaki.models import Work, SearchSimilarity
from mangaki.utils.ranking import TOP_MIN_RATINGS, RANDOM_MIN_RATINGS, RANDOM_MAX_DISLIKES, RANDOM_RATIO

from mangaki.factories import WorkFactory

class WorkQuerysetTest(TestCase):

    def setUp(self):
        try:
            self.works = WorkFactory.create_batch(20)
            self.assertEqual(len(self.works), 20)
        except StopIteration as e:
            pass

    def test_work_queryset_top(self):
        self.assertQuerysetEqual(Work.objects.top(), map(repr, Work.objects.filter(
            nb_ratings__gte=TOP_MIN_RATINGS).order_by(
                (F('sum_ratings') / F('nb_ratings')).desc()))
        )

    def test_work_queryset_popular(self):
        self.assertQuerysetEqual(Work.objects.popular(),
                map(repr, Work.objects.order_by('-nb_ratings')))

    def test_work_queryset_controversial(self):
        self.assertQuerysetEqual(Work.objects.controversial(),
                map(repr, Work.objects.order_by('-controversy')))

    def test_work_queryset_search(self):
        search_text = 'steins'
        self.assertQuerysetEqual(Work.objects.search(search_text),
            map(repr, Work.objects.filter(title__search=search_text)\
                .order_by(SearchSimilarity(F('title'), Value(search_text)).desc()))
        )

    def test_work_queryset_random(self):
        self.assertQuerysetEqual(Work.objects.random(),
            map(repr, Work.objects.filter(
                nb_ratings__gte=RANDOM_MIN_RATINGS,
                nb_dislikes__lte=RANDOM_MAX_DISLIKES,
                nb_likes__gte=F('nb_dislikes') * RANDOM_RATIO))
        )
