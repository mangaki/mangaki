from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Generator
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
    """
    date = date.strip()
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


class AniListAiringStatus(Enum):
    aired = 'finished airing'
    airing = 'currently airing'
    coming = 'not yet aired'
    cancelled = 'cancelled'


class AniListEntry:
    pass


class AniList:
    BASE_URL = "https://anilist.co/api/"
    AUTH_PATH = "auth/access_token"

    def __init__(self,
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None):
        if not client_id and client_secret:
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
        return self._auth["expires"] > time.time()

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

    def list_seasonal_animes(self) -> Generator[AniListEntry, None, None]:
        now = datetime.now()
        data = self._request(
            'browse/anime',
            query_params={
                'year': now.year,
                'season': to_anime_season(now),
                'status': AniListAiringStatus.airing.value
            }
        )

        for anime_info in data:
            yield AniListEntry(anime_info, AniListWorks.animes)

client = AniList(
    getattr(settings, 'ANILIST_CLIENT', None),
    getattr(settings, 'ANILIST_SECRET', None)
)
