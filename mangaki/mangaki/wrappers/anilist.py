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
    def __init__(self, anime_info, work_type: AniListWorks):
        self.anime_info = anime_info
        self.work_type = work_type

        if self.anime_info['series_type'] != work_type.value:
            raise ValueError('AniList data not from {}'.format(work_type.value))

    @property
    def anilist_id(self) -> int:
        return self.anime_info['id']

    @property
    def title(self) -> str:
        return self.anime_info['title_romaji']

    @property
    def english_title(self) -> str:
        return self.anime_info['title_english']

    @property
    def japanese_title(self) -> str:
        return self.anime_info['title_japanese']

    @property
    def media_type(self) -> str:
        return self.anime_info['type']

    @property
    def start_date(self) -> Optional[datetime]:
        if self.anime_info['start_date_fuzzy']:
            return to_python_datetime(self.anime_info['start_date_fuzzy'])
        return None

    @property
    def end_date(self) -> Optional[datetime]:
        if self.anime_info['end_date_fuzzy']:
            return to_python_datetime(self.anime_info['end_date_fuzzy'])
        return None

    @property
    def synonyms(self) -> List[str]:
        return list(filter(None, self.anime_info['synonyms']))

    @property
    def genres(self) -> List[str]:
        return list(filter(None, self.anime_info['genres']))

    @property
    def is_nsfw(self) -> bool:
        return self.anime_info['adult']

    @property
    def poster_url(self) -> str:
        return self.anime_info['image_url_lge']

    @property
    def nb_episodes(self) -> Optional[int]:
        if self.work_type == AniListWorks.animes:
            return self.anime_info['total_episodes']
        return None

    @property
    def nb_chapters(self) -> Optional[int]:
        if self.work_type == AniListWorks.mangas:
            return self.anime_info['total_chapters']
        return None

    @property
    def status(self) -> Optional[AniListStatus]:
        if self.work_type == AniListWorks.animes:
            return AniListStatus(self.anime_info['airing_status'])
        elif self.work_type == AniListWorks.mangas:
            return AniListStatus(self.anime_info['publishing_status'])
        else:
            return None

    @property
    def tags(self) -> List[Dict[str, Any]]:
        return [
            {
                'name': tag['name'],
                'anilist_tag_id': tag['id'],
                'spoiler': tag['spoiler'] or tag['series_spoiler']
            } for tag in self.anime_info['tags']
        ]

    def __str__(self) -> str:
        return '<AniListEntry {}#{} : {} - {}>'.format(
            self.work_type.value,
            self.anilist_id,
            self.title,
            self.status.value
        )


class AniListWorks(Enum):
    animes = 'anime'
    mangas = 'manga'


class AniListUserWork:
    __slots__ = ['title', 'poster', 'anilist_id', 'score']

    def __init__(self,
                 title: str,
                 poster: str,
                 anilist_id: int,
                 score: int):
        self.title = title
        self.poster = poster
        self.anilist_id = anilist_id
        self.score = score

    def __hash__(self):
        return hash(self.anilist_id)


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
        r.raise_for_status()
        return r.json()

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
                        anilist_id=int(list_entry['series_id']),
                        title=list_entry[worktype.value]['title_romaji'],
                        poster=list_entry[worktype.value]['image_url_lge'],
                        score=int(list_entry['score'])
                    )
                except KeyError:
                    raise RuntimeError('Malformed JSON, or AniList changed their API.')

client = AniList(
    getattr(settings, 'ANILIST_CLIENT', None),
    getattr(settings, 'ANILIST_SECRET', None)
)
