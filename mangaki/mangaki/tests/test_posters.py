# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from unittest.mock import patch, NonCallableMock

from django.test import TestCase

from mangaki.models import Editor, Studio, Work, Category

from mangaki.utils.db import get_potential_posters


class PostersTest(TestCase):

    def setUp(self):
        anime = Category.objects.get(slug='anime')

        self.kiznaiver = Work.objects.create(
            title='Kiznaiver',
            category=anime,
            ext_poster='bRoKeN_lInK'  # That's how I feel when I see a broken poster.
        )

    @patch('mangaki.utils.db.client.search_work')
    def test_get_potential_posters(self, mocked_search):
        with self.subTest('When MAL returns no poster'):
            expected = [{
                'current': True,
                'url': self.kiznaiver.ext_poster
            }]
            mocked_search.return_value = NonCallableMock(poster=None)
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
                'url': 'kiznaiver_mal_poster_url'
            }]
            mocked_search.return_value = NonCallableMock(poster=expected[1]['url'])
            posters = get_potential_posters(self.kiznaiver)
            # In this case, `get_potential_posters` should return a list of two posters, i.e. old external, MAL's one.
            self.assertCountEqual(posters, expected)
