from datetime import datetime
from urllib.parse import urljoin
import os

import responses
from django.conf import settings
from django.test import TestCase

from mangaki.models import (Work, WorkTitle, RelatedWork, Category, Genre,
                            Language, ExtLanguage, Artist, Staff, Studio)
from mangaki.wrappers.anilist import (fuzzydate_to_python_datetime, to_anime_season, read_graphql_query,
                                      AniList, AniListException, AniListStatus, AniListWorkType, AniListSeason,
                                      AniListMediaFormat, AniListRelation, AniListRelationType,
                                      insert_works_into_database_from_anilist, insert_work_into_database_from_anilist)


class AniListTest(TestCase):
    @staticmethod
    def read_fixture(filename):
        with open(os.path.join(settings.TEST_DATA_DIR, filename), 'r', encoding='utf-8') as f:
            return f.read()

    def setUp(self):
        self.anilist = AniList()

    def test_fuzzydate_to_python_datetime(self):
        self.assertEqual(fuzzydate_to_python_datetime({'year': 2017, 'month': 12, 'day': 25}), datetime(2017, 12, 25, 0, 0))
        self.assertEqual(fuzzydate_to_python_datetime({'year': 2017, 'month': 12, 'day': None}), datetime(2017, 12, 1, 0, 0))
        self.assertEqual(fuzzydate_to_python_datetime({'year': 2017, 'month': None, 'day': None}), datetime(2017, 1, 1, 0, 0))

        self.assertIsNone(fuzzydate_to_python_datetime({'year': None, 'month': None, 'day': 25}))
        self.assertIsNone(fuzzydate_to_python_datetime({'year': None, 'month': 12, 'day': 25}))
        self.assertIsNone(fuzzydate_to_python_datetime({'year': None, 'month': 12, 'day': None}))
        self.assertIsNone(fuzzydate_to_python_datetime({'year': None, 'month': None, 'day': None}))

    def test_to_anime_season(self):
        self.assertEqual(to_anime_season(datetime(2017, 1, 1, 0, 0)), AniListSeason.WINTER)
        self.assertEqual(to_anime_season(datetime(2017, 4, 1, 0, 0)), AniListSeason.SPRING)
        self.assertEqual(to_anime_season(datetime(2017, 7, 1, 0, 0)), AniListSeason.SUMMER)
        self.assertEqual(to_anime_season(datetime(2017, 10, 1, 0, 0)), AniListSeason.FALL)

    @responses.activate
    def test_api_errors(self):
        responses.add(
            responses.POST,
            self.anilist.BASE_URL,
            body='{ "data": { "Media": null }, "errors": [ { "message": "Not Found.", "status": 404, "locations": [{"line": 2, "column": 3}] } ] }',
            status=404,
            content_type='application/json'
        )

        with self.assertRaisesRegexp(AniListException, 'Error 404 : Not Found.'):
            self.anilist._request(
                query=read_graphql_query('work-info'),
                variables={'id': 0}
            )

    @responses.activate
    def test_get_work(self):
        responses.add(
            responses.POST,
            self.anilist.BASE_URL,
            body=self.read_fixture('anilist/hibike_euphonium.json'),
            status=200,
            content_type='application/json'
        )

        hibike_by_id = self.anilist.get_work(search_id=20912)
        hibike_by_title = self.anilist.get_work(search_title='Hibike')
        hibike_by_id_and_title = self.anilist.get_work(search_id=20912, search_title='Hibike')
        hibike = hibike_by_id_and_title

        self.assertEqual(hibike, hibike_by_id)
        self.assertEqual(hibike, hibike_by_title)

    @responses.activate
    def test_work_properties(self):
        responses.add(
            responses.POST,
            self.anilist.BASE_URL,
            body=self.read_fixture('anilist/hibike_euphonium.json'),
            status=200,
            content_type='application/json'
        )

        hibike = self.anilist.get_work(search_id=20912)

        self.assertEqual(hibike.anilist_id, 20912)
        self.assertEqual(hibike.anilist_url, 'https://anilist.co/anime/20912')
        self.assertEqual(hibike.media_format, AniListMediaFormat.TV)

        self.assertEqual(hibike.title, 'Hibike! Euphonium')
        self.assertEqual(hibike.english_title, 'Sound! Euphonium')
        self.assertEqual(hibike.japanese_title, '響け！ユーフォニアム')
        self.assertCountEqual(hibike.synonyms, [])

        self.assertEqual(hibike.start_date, datetime(2015, 4, 8, 0, 0))
        self.assertEqual(hibike.end_date, datetime(2015, 7, 1, 0, 0))
        self.assertEqual(hibike.season, AniListSeason.SPRING)

        self.assertEqual(hibike.description, 'The anime begins when Kumiko Oumae, a girl who was in the brass band club in junior high school, visits her high school\'s brass band club as a first year. Kumiko\'s classmates Hazuki and Sapphire decide to join the club, but Kumiko sees her old classmate Reina there and hesitates. She remembers an incident she had with Reina at a brass band club contest in junior high school...<br>\n<br>\n(Source: ANN)')
        self.assertCountEqual(hibike.genres, ['Music', 'Slice of Life', 'Drama'])
        self.assertFalse(hibike.is_nsfw)
        self.assertEqual(hibike.poster_url, 'https://cdn.anilist.co/img/dir/anime/reg/20912-vpZDPyqs22Rz.jpg')

        self.assertEqual(hibike.nb_episodes, 13)
        self.assertEqual(hibike.episode_length, 24)
        self.assertIsNone(hibike.nb_chapters)

        self.assertEqual(hibike.status, AniListStatus.FINISHED)
        self.assertEqual(hibike.studio, 'Kyoto Animation')

        self.assertCountEqual(hibike.external_links, {
            'Official Site': 'http://anime-eupho.com/',
            'Crunchyroll': 'http://www.crunchyroll.com/sound-euphonium',
            'Twitter': 'https://twitter.com/anime_eupho'
        })

        self.assertCountEqual(hibike.tags, [
            {'anilist_tag_id': 110, 'name': 'Band', 'spoiler': False, 'votes': 100},
            {'anilist_tag_id': 46, 'name': 'School', 'spoiler': False, 'votes': 79},
            {'anilist_tag_id': 98, 'name': 'Female Protagonist', 'spoiler': False, 'votes': 79},
            {'anilist_tag_id': 84, 'name': 'School Club', 'spoiler': False, 'votes': 73},
            {'anilist_tag_id': 50, 'name': 'Seinen', 'spoiler': False, 'votes': 33}
        ])

        self.assertEqual(len(hibike.staff), 13)

        self.assertCountEqual(hibike.relations, [
            AniListRelation(related_id=86133, relation_type=AniListRelationType.ADAPTATION),
            AniListRelation(related_id=21255, relation_type=AniListRelationType.SIDE_STORY),
            AniListRelation(related_id=21376, relation_type=AniListRelationType.SIDE_STORY),
            AniListRelation(related_id=21460, relation_type=AniListRelationType.SEQUEL),
            AniListRelation(related_id=21638, relation_type=AniListRelationType.SUMMARY),
            AniListRelation(related_id=100178, relation_type=AniListRelationType.SIDE_STORY)
        ])

    @responses.activate
    def test_get_seasonal_anime(self):
        responses.add(
            responses.POST,
            self.anilist.BASE_URL,
            body=self.read_fixture('anilist/airing_fall_2017.json'),
            status=200,
            content_type='application/json'
        )

        airing_animes = list(self.anilist.list_seasonal_animes(year=2017, season=AniListSeason.SUMMER))
        self.assertEqual(len(airing_animes), 36)

    @responses.activate
    def test_get_animelist(self):
        responses.add(
            responses.POST,
            self.anilist.BASE_URL,
            body=self.read_fixture('anilist/mrsalixor_anilist_animelist.json'),
            status=200,
            content_type='application/json'
        )

        anime_list = list(self.anilist.get_user_list(AniListWorkType.ANIME, 'mrsalixor'))
        self.assertEqual(len(anime_list), 450)

    @responses.activate
    def test_get_mangalist(self):
        responses.add(
            responses.POST,
            self.anilist.BASE_URL,
            body=self.read_fixture('anilist/mrsalixor_anilist_mangalist.json'),
            status=200,
            content_type='application/json'
        )

        anime_list = list(self.anilist.get_user_list(AniListWorkType.MANGA, 'mrsalixor'))
        self.assertEqual(len(anime_list), 100)

    @responses.activate
    def test_insert_into_database(self):
        artist = Artist(name='Ishihara Tatsuya').save()

        # Test insert AniListEntry into database
        responses.add(
            responses.POST,
            self.anilist.BASE_URL,
            body=self.read_fixture('anilist/hibike_euphonium.json'),
            status=200,
            content_type='application/json'
        )

        hibike_entry = self.anilist.get_work(search_id=20912)
        hibike = insert_work_into_database_from_anilist(hibike_entry, build_related=False)

        titles_hibike = WorkTitle.objects.filter(work=hibike).values_list('title', flat=True)
        genres_hibike = hibike.genre.values_list('title', flat=True)
        related_hibike = RelatedWork.objects.filter(parent_work=hibike)
        staff_hibike = Work.objects.get(pk=hibike.pk).staff_set.all().values_list('artist__name', flat=True)

        self.assertEqual(hibike.studio.title, 'Kyoto Animation')
        self.assertCountEqual(titles_hibike, ['Hibike! Euphonium', 'Sound! Euphonium', '響け！ユーフォニアム'])
        self.assertCountEqual(genres_hibike, ['Slice of Life', 'Music', 'Drama'])
        self.assertCountEqual(staff_hibike, ['Ishihara Tatsuya', 'Matsuda Akito', 'Takeda Ayano'])

        # Check for no artist duplication
        artist = Artist.objects.filter(name='Ishihara Tatsuya')
        self.assertEqual(artist.count(), 1)
        self.assertEqual(artist.first().anilist_creator_id, 100055)

        # Try adding this work to the DB again
        hibike_again = insert_work_into_database_from_anilist(hibike_entry, build_related=False)
        self.assertEqual(hibike, hibike_again)

    @responses.activate
    def test_update_work(self):
        fake_studio = Studio.objects.create(title='Fake Studio')
        hibike_outdated = Work.objects.create(
            category=Category.objects.get(slug='anime'),
            title='Sound! Euphonium',
            studio=fake_studio
        )
        hibike_outdated.genre.add(Genre.objects.create(title='Fake genre'))

        responses.add(
            responses.POST,
            self.anilist.BASE_URL,
            body=self.read_fixture('anilist/hibike_euphonium.json'),
            status=200,
            content_type='application/json'
        )

        hibike_entry = self.anilist.get_work(search_id=20912)
        # FIXME: properly mock the insertion of related works
        insert_work_into_database_from_anilist(hibike_entry, build_related=False)

        hibike_updated = Work.objects.get(title='Hibike! Euphonium')

        titles_hibike = WorkTitle.objects.filter(work=hibike_updated).values_list('title', flat=True)
        genres_hibike = hibike_updated.genre.values_list('title', flat=True)
        related_hibike = RelatedWork.objects.filter(parent_work=hibike_updated)
        staff_hibike = Work.objects.get(pk=hibike_updated.pk).staff_set.all().values_list('artist__name', flat=True)

        self.assertEqual(hibike_updated.studio.title, 'Kyoto Animation')
        self.assertCountEqual(titles_hibike, ['Hibike! Euphonium', 'Sound! Euphonium', '響け！ユーフォニアム'])
        self.assertCountEqual(genres_hibike, ['Slice of Life', 'Music', 'Drama'])
        self.assertCountEqual(staff_hibike, ['Ishihara Tatsuya', 'Matsuda Akito', 'Takeda Ayano'])
