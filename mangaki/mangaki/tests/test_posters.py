from unittest.mock import patch, MagicMock, PropertyMock

from django.test import TestCase

from mangaki.models import Editor, Studio, Work, Category

from mangaki.utils.db import get_potential_posters


class PostersTest(TestCase):

    def setUp(self):
        # FIXME: The defaults for editor and studio in Work requires those to
        # exist, or else foreign key constraints fail.
        Editor.objects.create(pk=1)
        Studio.objects.create(pk=1)

        anime = Category.objects.get(slug='anime')

        self.kiznaiver = Work.objects.create(
            title='Kiznaiver',
            category=anime,
            ext_poster='bRoKeN_lInK'  # That's how I feel when I see a broken poster.
        )

    # We only want to abstract the MAL search implementation.
    @patch('mangaki.utils.db.client.search_work')
    def test_get_potential_posters(self, mocked_search):
        with self.subTest('When MAL returns no poster'):
            expected = [{
                'current': True,
                'url': self.kiznaiver.ext_poster
            }]
            # Set up mocks.
            mocked_entry = MagicMock()
            # Pay no mind to this ugliness:
            # https://docs.python.org/3/library/unittest.mock.html#unittest.mock.PropertyMock
            type(mocked_entry).poster = PropertyMock(return_value=None)
            mocked_search.return_value = mocked_entry
            # Let the magic occur.
            posters = get_potential_posters(self.kiznaiver)
            # In this case, `get_potential_posters` cannot fix the current poster.
            self.assertCountEqual(posters, expected)

        with self.subTest('When MAL returns a poster'):
            expected = [{
                'current': True,
                'url': self.kiznaiver.ext_poster
            }, {
                'current': False,
                'url': 'some_good_poster_with_waifus'
            }]
            # Set up the mocks.
            mocked_entry = MagicMock()
            # Pay no mind to this ugliness (refer to link mentioned above for information).
            type(mocked_entry).poster = PropertyMock(return_value=expected[1]['url'])
            mocked_search.return_value = mocked_entry
            # Let the magic occur.
            posters = get_potential_posters(self.kiznaiver)
            # In this case, `get_potential_posters` should return a list of two posters, i.e. old external, MAL's one.
            self.assertCountEqual(posters, expected)
