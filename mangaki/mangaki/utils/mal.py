"""
This module contains multiple functions to interact with MyAnimeList API,
looking for anime and finding URL of posters.
"""

import xml.etree.ElementTree as ET
from enum import Enum
from typing import Optional, List, Generator

import requests
import html
import re
from functools import reduce

from django.conf import settings

from django.contrib.auth.models import User
from django.db.models import QuerySet, Q

from mangaki.models import Work, Rating, SearchIssue, Category

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


MALUserWork = namedtuple('MALUserWork', 'title poster mal_id score')


class MALEntry:
    def __init__(self, xml_entry, work_type: MALWorks):
        self.xml = xml_entry
        self.raw_properties = {child.tag: child.text for child in xml_entry}
        self.work_type = work_type

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
                poster = entry.find('series_image').text
                score = int(entry.find('my_score').text)
                mal_id = entry.find('series_{}db_id'.format(work_type.value)).text
            except AttributeError:
                logger.exception('Malformed XML response (or MAL changed its API!)')
                continue

            yield MALUserWork(
                title=title,
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


def insert_into_mangaki_database_from_mal(mal_entries: List[MALEntry]):
    # Assumption: Mangaki's slugs are the same as MAL's work types.
    if not mal_entries:
        return

    # All entries are supposed of the same type.
    work_cat = Category.objects.get(slug=mal_entries[0].work_type.value)
    for entry in mal_entries:
        is_present = Work.objects.filter(
            category=work_cat,
            ext_poster=entry.poster
        ).exists()

        if not is_present:
            Work.objects.create(
                category=work_cat,
                title=entry.english_title or entry.title,
                source=entry.source_url,
                ext_poster=entry.poster,
                date=entry.start_date
            )


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
    :param poster_link: poster URL of the work
    :type poster_link: str
    :return: a new work or already existing work!
    :rtype: Work
    """
    try:
        return work_list.get(title__iexact=title)
    except Work.MultipleObjectsReturned:
        works = work_list.filter(title__iexact=title).values_list('id').all()
        logger.warning('Duplicates detected (title) for the work <{}> -- selecting first.'.format(title))
        return works[0]
    except Work.DoesNotExist:
        count = work_list.filter(ext_poster=poster_link).count()
        if count == 1:
            return Work.objects.get(ext_poster=poster_link)
        elif count >= 2:
            logger.warning('Duplicates detected (ext_poster) for work with <{}> (during <{}> import) '
                           '-- selecting first.'
                           .format(poster_link, title))
            return Work.objects.filter(ext_poster=poster_link).first()
        else:
            works = client.search_works(work_type, title)
            insert_into_mangaki_database_from_mal(works)
            return work_list.filter(
                Q(ext_poster=poster_link)
                | Q(title__iexact=title)).first()


def import_mal(mal_username: str, mangaki_username: str):
    """
    Import myAnimeList by username
    """

    user = User.objects.get(username=mangaki_username)
    nb_added = 0
    fails = []
    mangaki_lists = {
        MALWorks.animes: Work.objects.filter(category__slug='anime'),
        MALWorks.mangas: Work.objects.filter(category__slug='manga')
    }

    for work_type in SUPPORTED_MANGAKI_WORKS:
        for user_work in client.list_works_from_a_user(work_type, mal_username):
            try:
                work = get_or_create_from_mal(
                    mangaki_lists[work_type],
                    work_type,
                    user_work.title,
                    user_work.poster)

                if work:
                    already_rated = Rating.objects.filter(user=user, work=work).exists()
                    if not already_rated:
                        choice = compute_rating_choice_from_mal_score(user_work.score)
                        if not choice:
                            raise RuntimeError('No choice was deduced from MAL score.')

                        Rating(user=user, choice=choice, work=work).save()

                    nb_added += 1
            except Exception:
                logger.exception('Failure to fetch the work from MAL and import it into the Mangaki database.')
                SearchIssue(
                    user=user,
                    title=user_work.title,
                    poster=user_work.poster,
                    mal_id=user_work.mal_id,
                    score=user_work.score).save()
                fails.append(user_work.title)

    return nb_added, fails
