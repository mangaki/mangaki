from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Generator
from urllib.parse import urljoin
import time

import requests
from django.utils.functional import cached_property

from mangaki import settings
from mangaki.models import Category


def to_python_datetime(date):
    """
    Converts AniList's fuzzydate to Python datetime format.
    >>> to_python_datetime('20150714')
    datetime.datetime(2015, 7, 14, 0, 0)
    >>> to_python_datetime('20150700')
    datetime.datetime(2015, 7, 1, 0, 0)
    >>> to_python_datetime('20150000')
    datetime.datetime(2015, 1, 1, 0, 0)
    >>> to_python_datetime('2015')
    Traceback (most recent call last):
     ...
    ValueError: no valid date format found for 2015
    """
    date = str(date).strip()
    for fmt in ('%Y%m%d', '%Y%m00', '%Y0000'):
        try:
            return datetime.strptime(date, fmt)
        except ValueError:
            pass
    raise ValueError('no valid date format found for {}'.format(date))

def to_anime_season(date):
    """
    Return the season corresponding to a date
    >>> to_anime_season(datetime.datetime(2017, 3, 3, 0, 0))
    'winter'
    """
    if 1 <= date.month <= 3:
        return 'winter'
    elif 4 <= date.month <= 6:
        return 'spring'
    elif 7 <= date.month <= 9:
        return 'summer'
    else:
        return 'fall'


class AniListWorks(Enum):
    animes = 'anime'
    mangas = 'manga'


class AniListStatus(Enum):
    aired = 'finished airing'
    airing = 'currently airing'
    published = 'finished publishing'
    publishing = 'publishing'
    anime_coming = 'not yet aired'
    manga_coming = 'not yet published'
    cancelled = 'cancelled'


class AniListEntry:
    def __init__(self, work_info, work_type: AniListWorks):
        self.work_info = work_info
        self.work_type = work_type

        if self.work_info['series_type'] != work_type.value:
            raise ValueError('AniList data not from {}'.format(work_type.value))

    @property
    def anilist_id(self) -> int:
        return self.work_info['id']

    @property
    def title(self) -> str:
        return self.work_info['title_romaji']

    @property
    def english_title(self) -> str:
        return self.work_info['title_english']

    @property
    def japanese_title(self) -> str:
        return self.work_info['title_japanese']

    @property
    def media_type(self) -> str:
        return self.work_info['type']

    @property
    def start_date(self) -> Optional[datetime]:
        if self.work_info['start_date_fuzzy']:
            return to_python_datetime(self.work_info['start_date_fuzzy'])
        return None

    @property
    def end_date(self) -> Optional[datetime]:
        if self.work_info['end_date_fuzzy']:
            return to_python_datetime(self.work_info['end_date_fuzzy'])
        return None

    @property
    def description(self) -> Optional[str]:
        return self.work_info.get('description')

    @property
    def synonyms(self) -> List[str]:
        return list(filter(None, self.work_info['synonyms']))

    @property
    def genres(self) -> List[str]:
        return list(filter(None, self.work_info['genres']))

    @property
    def is_nsfw(self) -> bool:
        return self.work_info['adult']

    @property
    def poster_url(self) -> str:
        return self.work_info['image_url_lge']

    @property
    def nb_episodes(self) -> Optional[int]:
        if self.work_type == AniListWorks.animes:
            return self.work_info['total_episodes']
        return None

    @property
    def episode_length(self) -> Optional[int]:
        if self.work_type == AniListWorks.animes:
            return self.work_info.get('duration')
        return None

    @property
    def nb_chapters(self) -> Optional[int]:
        if self.work_type == AniListWorks.mangas:
            return self.work_info['total_chapters']
        return None

    @property
    def status(self) -> Optional[AniListStatus]:
        if self.work_type == AniListWorks.animes:
            return AniListStatus(self.work_info['airing_status'])
        elif self.work_type == AniListWorks.mangas:
            return AniListStatus(self.work_info['publishing_status'])
        return None

    @property
    def tags(self) -> Optional[List[Dict[str, Any]]]:
        if self.work_info.get('tags'):
            return [
                {
                    'name': tag['name'],
                    'anilist_tag_id': tag['id'],
                    'spoiler': tag['spoiler'] or tag['series_spoiler'],
                    'votes': tag['votes']
                } for tag in self.work_info['tags']
            ]
        return None

    def __str__(self) -> str:
        return '<AniListEntry {}#{} : {} - {}>'.format(
            self.work_type.value,
            self.anilist_id,
            self.title,
            self.status.value
        )


class AniListRichEntry(AniListEntry):
    def __init__(self, work_info, work_type: AniListWorks):
        super().__init__(work_info, work_type)
        self._build_external_links()

    @property
    def studio(self) -> Optional[str]:
        if self.work_info.get('studio'):
            for studio in self.work_info.get('studio'):
                if studio['main_studio'] == 1:
                    return studio['studio_name']
        return None

    @property
    def youtube_url(self) -> Optional[str]:
        if self.work_info.get('youtube_id'):
            return 'https://www.youtube.com/watch?v={}'.format(self.work_info['youtube_id'])
        return None

    def _build_external_links(self):
        if self.work_info.get('external_links'):
            for link in self.work_info.get('external_links'):
                if link['site'] == 'Crunchyroll':
                    self.crunchyroll_url = link['url']
                elif link['site'] == 'Twitter':
                    self.twitter_url = link['url']
                elif link['site'] == 'Official Site':
                    self.official_url = link['url']

    @property
    def relations(self):
        pass


class AniListWorks(Enum):
    animes = 'anime'
    mangas = 'manga'


class AniListUserWork:
    __slots__ = ['work', 'score']

    def __init__(self,
                 work: AniListEntry,
                 score: int):
        self.work = work
        self.score = score

    def __hash__(self):
        return hash(self.work.anilist_id)


class AniList:
    BASE_URL = "https://anilist.co/api/"
    AUTH_PATH = "auth/access_token"

    def __init__(self,
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None):
        if not client_id or not client_secret:
            self.is_available = False
        else:
            self.is_available = True

            self.client_id = client_id
            self.client_secret = client_secret

            self._cache = {}
            self._session = requests.Session()
            self._auth = None

    def _authenticate(self):
        if not self.is_available:
            raise RuntimeError('AniList API is not available!')

        params = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        r = self._session.post(urljoin(self.BASE_URL, self.AUTH_PATH), data=params)
        r.raise_for_status()

        self._auth = r.json()
        self._session.headers['Authorization'] = 'Bearer ' + self._auth['access_token']

        return self._auth

    def _is_authenticated(self):
        if not self.is_available:
            return False
        if self._auth is None:
            return False
        return self._auth['expires'] > time.time()

    def _request(self,
                 datapage: str,
                 params: Optional[Dict[str, str]] = None,
                 query_params: Optional[Dict[str, str]] = None):
        """
        Request an Anilist API's page (see https://anilist-api.readthedocs.io/en/latest/ for more)
        >>> self._request("{series_type}/{id}", params={"series_type": "anime", "id": "5"})
        Returns a series model as a JSON.
        >>> self._request("browse/{series_type}", params={"series_type": "anime"}, query_params={"year": "2017"})
        Returns up to 40 small series models where year is 2017 as a JSON.
        """
        if not self._is_authenticated():
            self._authenticate()

        if params is None:
            params = {}

        if query_params is None:
            query_params = {}

        r = self._session.get(urljoin(self.BASE_URL, datapage.format(**params)), params=query_params)
        if r.status_code == 404:
            return None
        r.raise_for_status()

        data = r.json()
        # Check if data is a list of JSON objects
        if isinstance(data, list):
            return data
        # Check if data is a single JSON object
        else:
            # Check that the JSON return is not an error (eg. No Results)
            if data.get('error'):
                return None
        return data

    def list_seasonal_animes(self,
                             *,
                             only_airing: Optional[bool] = True,
                             year: Optional[int] = None,
                             season: Optional[str] = None) -> Generator[AniListEntry, None, None]:
        if not year or not season:
            now = datetime.now()
            year = now.year
            season = to_anime_season(now)

        query_params = {'year': year, 'season': season, 'full_page': 'true'}

        if only_airing:
            query_params.update({'status': AniListStatus.airing.value})

        data = self._request('browse/anime', query_params=query_params)
        for anime_info in data:
            yield AniListEntry(anime_info, AniListWorks.animes)

    def get_work_by_id(self,
                       worktype: AniListWorks,
                       id: int) -> AniListRichEntry:
        """
        Search a work by ID on AniList and returns a rich entry if the ID exists,
        or None if there are no results.
        A rich entry has informations about characters, staff, studio and even
        related works.
        """
        data = self._request(
            '{worktype}/{id}/page',
            {'worktype': worktype.value, 'id': id}
        )

        if data:
            return AniListRichEntry(data, worktype)
        return None

    def get_work_by_title(self,
                          worktype: AniListWorks,
                          title: str) -> AniListEntry:
        """
        Search a work by title on AniList and returns the first result if there
        are results, or None if there are no results.
        AniList searches a work by romaji, English or Japanese title and even
        by synonym titles.
        """
        data = self._request(
            '{worktype}/search/{title}',
            {'worktype': worktype.value, 'title': title}
        )

        if data:
            return AniListEntry(data[0], worktype)
        return None

    def get_user_list(self,
                      worktype: AniListWorks,
                      username: str) -> Generator[AniListUserWork, None, None]:
        data = self._request(
            'user/{username}/{worktype}list',
            {'username': username, 'worktype': worktype.value}
        )

        for list_type in data['lists']:
            for list_entry in data['lists'][list_type]:
                try:
                    yield AniListUserWork(
                        work=AniListEntry(list_entry[worktype.value], worktype),
                        score=int(list_entry['score'])
                    )
                except KeyError:
                    raise RuntimeError('Malformed JSON, or AniList changed their API.')

client = AniList(
    getattr(settings, 'ANILIST_CLIENT', None),
    getattr(settings, 'ANILIST_SECRET', None)
)
