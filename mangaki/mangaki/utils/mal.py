"""
This module contains multiple functions to interact with MyAnimeList API,
looking for anime and finding URL of posters.
"""

import xml.etree.ElementTree as ET
from enum import Enum
from typing import Optional, List, Generator, Set

import requests
import html
import re
from functools import reduce

from django.conf import settings

from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchQuery
from django.db.models import QuerySet, Q
from django.db import transaction

from mangaki.models import Work, Rating, SearchIssue, Category, WorkTitle

from collections import namedtuple

import logging

logger = logging.getLogger(__name__)


def _encoding_translation(text):
    translations = {
        '&lt': '&lot;',
        '&gt;': '&got;',
        '&lot;': '&lt',
        '&got;': '&gt;'
    }

    return reduce(lambda s, r: s.replace(*r), translations.items(), text)


# User-friendly representation of works' type.
class MALWorks(Enum):
    animes = 'anime'
    mangas = 'manga'
    novels = 'novel'


SUPPORTED_MANGAKI_WORKS = [MALWorks.animes, MALWorks.mangas]


class MALUserWork:
    __slots__ = ['title', 'synonyms', 'poster', 'mal_id', 'score']

    def __init__(self,
                 title: str,
                 synonyms: List[str],
                 poster: str,
                 mal_id: str,
                 score: float):
        self.title = title
        self.synonyms = synonyms
        self.poster = poster
        self.mal_id = mal_id
        self.score = score

    def __hash__(self):
        return hash(self.mal_id)


class MALEntry:
    def __init__(self, xml_entry, work_type: MALWorks):
        self.xml = xml_entry
        self.raw_properties = {child.tag: child.text for child in xml_entry}
        self.work_type = work_type
        self.anime_type = None
        self.manga_type = None

        if self.work_type == MALWorks.animes:
            self.anime_type = self.raw_properties['type'].lower()
        elif (self.work_type == MALWorks.mangas
              and self.raw_properties.get('type').lower() == MALWorks.novels):
            # MAL(stupidity): You thought it was a manga! It's a light novel !
            self.work_type = MALWorks.novels
        elif self.work_type == MALWorks.mangas:
            self.manga_type = self.raw_properties['type'].lower()

    @property
    def poster(self) -> Optional[str]:
        return self.raw_properties.get('image', None)

    @property
    def english_title(self) -> Optional[str]:
        return self.raw_properties.get('english', None)

    @property
    def title(self) -> str:
        return self.raw_properties.get('title', None)

    @property
    def start_date(self) -> Optional[str]:
        xml_date = self.raw_properties.get('start_date', None)
        if not xml_date or '0000' in xml_date:
            return None

        if '-00-00' in xml_date:
            return xml_date.replace('-00-00', '-01-01')

        if '-00' in xml_date:
            return xml_date.replace('-00', '-01')

        return xml_date

    @property
    def source_url(self) -> str:
        return (
            'https://myanimelist.net/{}/{}'.format(self.work_type.value, self.raw_properties['id'])
        )

    @property
    def mal_id(self) -> int:
        return int(self.raw_properties['id'])

    @property
    def synonyms(self) -> List[str]:
        if not self.raw_properties.get('synonyms'):
            return []

        return [synonym.strip() for synonym in self.raw_properties['synonyms'].split(';')]

    @property
    def nb_episodes(self) -> Optional[int]:
        if not self.raw_properties.get('episodes'):
            return None

        return int(self.raw_properties.get('episodes'))

    def __str__(self) -> str:
        return '<MALEntry {} - {} - {}>'.format(
            self.mal_id,
            self.title,
            self.work_type.value
        )


class MALClient:
    SEARCH_URL = 'https://myanimelist.net/api/{type}/search.xml'
    LIST_WORK_URL = 'https://myanimelist.net/malappinfo.php?u={username}&status=all&type={type}'
    HEADERS = {
        'User-Agent': getattr(settings, 'MAL_USER_AGENT', 'mangaki')
    }

    def __init__(self,
                 mal_user: Optional[str] = None,
                 mal_pass: Optional[str] = None):
        if not mal_user or not mal_pass:
            self.is_available = False
        else:
            self.session = requests.Session()
            self.session.headers = self.HEADERS
            self.session.auth = (mal_user, mal_pass)
            self.is_available = True

    @staticmethod
    def _translate_http_exceptions(resp: requests.Response) -> None:
        if resp.status_code == requests.codes['FORBIDDEN']:
            raise RuntimeError('Invalid MAL credentials!')

        if not resp.status_code == requests.codes['ALL_GOOD']:
            raise RuntimeError('MAL request failure!')

    def list_works_from_a_user(self,
                               work_type: MALWorks,
                               username: str) -> Generator[MALUserWork, None, None]:
        resp = (
            self.session.get(
                self.LIST_WORK_URL.format(
                    username=username,
                    type=work_type.value)
            )
        )

        xml = ET.fromstring(resp.text)
        for entry in xml:
            # Skip the myinfo part.
            if entry.tag == 'myinfo':
                continue
            try:
                title = entry.find('series_title').text
                synonyms_node = entry.find('series_synonyms').text
                if synonyms_node:
                    # Take all non-empty synonyms.
                    stripped_synonyms = (
                        syn.strip()
                        for syn in entry.find('series_synonyms').text.split('; ')
                    )
                    synonyms = list(filter(None, stripped_synonyms))
                else:
                    synonyms = []
                poster = entry.find('series_image').text
                score = int(entry.find('my_score').text)
                mal_id = entry.find('series_{}db_id'.format(work_type.value)).text
            except AttributeError:
                logger.exception('Malformed XML response (or MAL changed its API!)')
                continue

            yield MALUserWork(
                title=title,
                synonyms=synonyms,
                poster=poster,
                mal_id=mal_id,
                score=score)

    def _search_api(self, work_type: MALWorks, query: str) -> requests.Response:
        return self.session.get(
            self.SEARCH_URL.format(type=work_type.value),
            params={
                'q': query
            })

    def _search_works(self, work_type: MALWorks, query: str) -> str:
        resp = self._search_api(work_type, query)
        self._translate_http_exceptions(resp)

        html_code = html.unescape(re.sub(r'&amp;([A-Za-z]+);', r'a\1;', resp.text))
        xml = re.sub(r'&([^alg])', r'&amp;\1', _encoding_translation(html_code))

        return xml

    def search_work(self, work_type: MALWorks, query: str) -> MALEntry:
        xml = self._search_works(work_type, query)

        return MALEntry(ET.fromstring(xml).find('entry'), work_type)

    def search_works(self, work_type: MALWorks, query: str) -> List[MALEntry]:
        xml = self._search_works(work_type, query)

        entries = []
        for entry in ET.fromstring(xml).findall('entry'):
            try:
                mal_entry = MALEntry(entry, work_type)
                entries.append(mal_entry)
            except ET.ParseError:
                logger.exception('MAL parsing error during search')

            return entries


client = MALClient(getattr(settings, 'MAL_USER', None),
                   getattr(settings, 'MAL_PASS', None))


def lookup_works(work_list: QuerySet,
                 ext_poster: str,
                 titles: List[str]) -> List[Work]:
    """
    Look into the database all the works
    matching one of the `titles` or the external poster.

    Raise ValueError when no `titles` (empty list) are given.

    :param work_list: A (filtered) QuerySet from Django starting from the Work model
    :type work_list: A queryset, e.g. `Work.objects.filter(category__slug='anime')`
    :param ext_poster: A string path to the external poster (a URL link)
    :type ext_poster: string
    :param titles: A list of potential titles that the work can hold, e.g. synonyms and unofficial titles.
    :type titles: list of strings
    :return: a list of matching works (can be empty)
    :rtype: list of Work objects
    """
    if len(titles) == 0:
        raise ValueError('Empty list of `titles` !')

    constraints_work = constraints_title = reduce(
        lambda x, y: x | y,
        (
            SearchQuery(syn, config='simple')
            for syn in titles
        )
    )
    constraints_work = Q(title_search=constraints_work) | Q(ext_poster=ext_poster)

    works_ids_matched = set(work_list.filter(constraints_work)
                            .values_list('id', flat=True)[:2])
    titles_ids_matched = set(
        WorkTitle.objects
            .filter(title_search=constraints_title)
            .values_list('work_id', flat=True).all()
    )

    return list(Work.objects.in_bulk(titles_ids_matched | works_ids_matched).values())


def insert_into_mangaki_database_from_mal(mal_entries: List[MALEntry],
                                          title: Optional[str] = None) -> Optional[Work]:
    """
    Insert into Mangaki database from MAL data.
    And return the work corresponding to the title.
    :param mal_entries: a list of entries that will be inserted into the database if not present
    :type mal_entries: List[MALEntry]
    :param title: title of work looked for (optional)
    :type title: str (can be None)
    :return: a work if title is specified
    :rtype: Optional[Work]
    """
    # Assumption: Mangaki's slugs are the same as MAL's work types.
    if not mal_entries:
        return

    first_matching_work = None

    # All entries are supposed of the same type.
    work_cat = Category.objects.get(slug=mal_entries[0].work_type.value)
    for entry in mal_entries:
        # Check over all known titles.
        titles = [entry.title]
        if entry.english_title:
            titles.append(entry.english_title)

        is_present = (
            len(lookup_works(
                Work.objects.filter(
                    category=work_cat
                ),
                entry.poster,
                titles
            )) > 0
        )

        if not is_present:
            extra_fields = {}
            if entry.nb_episodes:
                extra_fields['nb_episodes'] = entry.nb_episodes

            work = Work.objects.create(
                category=work_cat,
                title=entry.english_title or entry.title,
                source=entry.source_url,
                ext_poster=entry.poster,
                date=entry.start_date,
                **extra_fields
            )

            if (title and not first_matching_work
                and title.upper() in list(map(str.upper, titles))):
                first_matching_work = work

            work_titles = [
                WorkTitle(
                    work=work,
                    title=synonym,
                    language=None,
                    type='synonyme'
                )
                for synonym in entry.synonyms
            ]

            # TODO: we should add entry.english_title as main title.
            # After Language is split into ExtLanguage and Language.

            if work_titles:
                WorkTitle.objects.bulk_create(work_titles)

                # FIXME: add ext genre, ext type.
                # Tracked in https://github.com/mangaki/mangaki/issues/339

    return first_matching_work


def poster_url(work_type: MALWorks, query: str) -> str:
    """
    Look for an anime on MyAnimeList and return the URL of its poster.
    """

    return client.search_work(work_type, query).poster


def compute_rating_choice_from_mal_score(score: int) -> Optional[str]:
    """
    Compute from the MAL score, "the Mangaki choice" (like, neutral, favorite, dislike).
    :param score: an integer between 0 and 10
    :type score: int
    :return: None if the score is out of the range, otherwise, [7, 10] => like, [5, 6] => neutral, [0, 4] => dislike.
    :rtype: Optional[str]
    
    
    >>> compute_rating_choice_from_mal_score(8)
    'like'
    >>> compute_rating_choice_from_mal_score(-1)
    >>> compute_rating_choice_from_mal_score(0)
    'dislike'
    >>> compute_rating_choice_from_mal_score(5)
    'neutral'
    """
    if 7 <= score <= 10:
        return 'like'
    elif 5 <= score <= 6:
        return 'neutral'
    elif score >= 0:
        return 'dislike'
    else:
        return None


def get_or_create_from_mal(work_list: QuerySet,
                           work_type: MALWorks,
                           title: str,
                           synonyms: List[str],
                           poster_link: str) -> Optional[Work]:
    """
    Get a work from the current `work_list` (a queryset, filtered by category)
    or create from scratch using MAL as reference.
    
    :param work_list: a QuerySet of works
    :type work_list: QuerySet<Work>
    :param work_type: type of the work considered (e.g. MALWorks.animes)
    :type work_type: MALWorks enum
    :param title: title of the work
    :type title: str
    :param synonyms: list of alternative titles
    :type synonyms: list of str
    :param poster_link: poster URL of the work
    :type poster_link: str
    :return: a new work or already existing work!
    :rtype: Work
    """
    # Either, we find something with the good poster or one of the good titles.
    # Also looking into WorkTitle as it is available.
    items = lookup_works(work_list, poster_link, [title] + synonyms)

    if len(items) == 1:
        return items[0]
    elif len(items) > 1:
        logger.warning('Duplicates detected (titles) for the work <{}> -- selecting first.'.format(title))
        return items[0]
    else:
        logger.info('Fetching new works using MAL ({})'.format(title))
        works = client.search_works(work_type, title)
        # Return the first matching work while inserting into DB.
        return insert_into_mangaki_database_from_mal(works, title)


@transaction.atomic
def import_mal(mal_username: str, mangaki_username: str):
    """
    Import myAnimeList by username
    """

    user = User.objects.get(username=mangaki_username)
    fails = []
    mangaki_lists = {
        MALWorks.animes: Work.objects.filter(category__slug='anime'),
        MALWorks.mangas: Work.objects.filter(category__slug='manga')
    }
    scores = {}

    for work_type in SUPPORTED_MANGAKI_WORKS:
        user_works = set(
            client.list_works_from_a_user(work_type, mal_username)
        )
        logger.info('Fetching {} works from {}\'s MAL.'.format(len(user_works), mal_username))
        for user_work in user_works:
            try:
                work = get_or_create_from_mal(
                    mangaki_lists[work_type],
                    work_type,
                    user_work.title,
                    user_work.synonyms,
                    user_work.poster)

                if work:
                    scores[work.id] = user_work.score
            except Exception:
                logger.exception('Failure to fetch the work from MAL and import it into the Mangaki database.')
                SearchIssue(
                    user=user,
                    title=user_work.title,
                    poster=user_work.poster,
                    mal_id=user_work.mal_id,
                    score=user_work.score).save()
                fails.append(user_work.title)

    existing_ratings = (
        Rating.objects.filter(user=user, work__in=scores.keys())
            .values_list('work', flat=True)
            .all()
    )

    for related_work_id in existing_ratings:
        del scores[related_work_id]

    ratings = []
    for work_id, score in scores.items():
        choice = compute_rating_choice_from_mal_score(score)
        if not choice:
            raise RuntimeError('No choice was deduced from MAL score!')

        rating = Rating(user=user, choice=choice, work_id=work_id)
        ratings.append(rating)

    Rating.objects.bulk_create(ratings)

    return len(ratings), fails
