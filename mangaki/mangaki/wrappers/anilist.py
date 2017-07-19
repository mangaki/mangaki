from datetime import datetime
from typing import Dict, List, Optional
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
    date = date.strip()
    for fmt in ('%Y%m%d', '%Y%m00', '%Y0000'):
        try:
            return datetime.strptime(date, fmt)
        except ValueError:
            pass
    raise ValueError('no valid date format found for {}'.format(date))


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

client = AniList(
    getattr(settings, 'ANILIST_CLIENT', None),
    getattr(settings, 'ANILIST_SECRET', None)
)
