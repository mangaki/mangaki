from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from django.utils.functional import cached_property

from mangaki import settings
from mangaki.models import Category


def to_python_datetime(date):
    """
    Converts AniList's fuzzydate to Python datetime format.
    >>> to_python_datetime('20150714')
    datetime.datetime(2015, 7, 14, 0, 0)
    """
    date = date.strip()

    year = int(date[0:4])
    month = int(date[4:6])
    day = int(date[6:8])

    return datetime(year, month, day)


class AniList:
    BASE_URL = "https://anilist.co/api"
    AUTH_PATH = "auth/access_token"

    def __init__(self,
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None):
        if not client_id and client_secret:
            self.is_available = False
        else:
            self.client_id = client_id
            self.client_secret = client_secret
            self._cache = {}
            self._auth = None
            self._session = requests.Session()
            self.is_available = True

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

        return self._auth

    def _request(self, datapage, params=None):
        if not self._auth:
            self._authenticate()

        if not self.is_available:
            raise RuntimeError('AniDB API is not available!')

        if params is None:
            params = {}

    @cached_property
    def anime_category(self) -> Category:
        return Category.objects.get(slug='anime')

client = AniList(
    getattr(settings, 'ANILIST_CLIENT', None),
    getattr(settings, 'ANILIST_SECRET', None)
)
