import requests
from bs4 import BeautifulSoup
from datetime import datetime
from mangaki.models import Language

BASE_URL = "http://api.anidb.net:9001/httpapi"
SEARCH_URL = "http://anisearch.outrance.pl/"
PROTOCOL_VERSION = 1

try:
    str = unicode
except:
    pass
    # str = str


class AniDB:
    def __init__(self, client_id, client_ver=0):
        self.client_id = client_id
        self.client_ver = client_ver
        self._cache = {}

    def _request(self, datapage, params={}, cache=True):
        params.update({
                       'client': self.client_id,
                       'clientver': self.client_ver,
                       'protover': PROTOCOL_VERSION,
                       'request': datapage
                      })
        r = requests.get(BASE_URL, params=params)
        r.raise_for_status()
        return r

    # Anime http://wiki.anidb.net/w/HTTP_API_Definition#Access

    def search(self, q):
        """
        Search for `aid`s by anime title using service provided by eloyard.
        http://anisearch.outrance.pl/doc.html
        """
        r = requests.get(SEARCH_URL, params={
          'task': "search",
          'query': q,
        })
        r.raise_for_status()
        results = []
        animetitles = BeautifulSoup(r.text, 'xml').animetitles
        for anime in animetitles.find_all('anime'):
            results.append(Anime({
            'id': int(anime['aid']),
            'title': str(anime.find('title', attrs={'type': "official"}).string)
            }, partial=True, updater=lambda: self.get(anime['id'])))

        return results

    def get(self, id):
        """
        Allows retrieval of non-file or episode related information for a specific anime by AID (AniDB anime id).
        http://wiki.anidb.net/w/HTTP_API_Definition#Anime
        """
        id = int(id) # why?

        r = self._request("anime", {'aid': id})
        soup = BeautifulSoup(r.text.encode('utf-8'), 'xml')  # http://stackoverflow.com/questions/31126831/beautifulsoup-with-xml-fails-to-parse-full-unicode-strings#comment50430922_31146912
        """with open('backup.xml', 'w') as f:
           f.write(r.text)"""
        if soup.error is not None:
            raise Exception(soup.error.string)

        anime = soup.anime
        titles = anime.titles

        languages = {language.anidb_language: language.iso639 for language in Language.objects.all()}
        a = Anime({
        'id': id,

        'worktitles': [(title.string, languages[title['xml:lang']])
                        for title in titles.find_all('title')
                        if title['type'] != 'short' and title['xml:lang'] in languages],
        'type': str(anime.type.string),
        'episodecount': int(anime.episodecount.string),
        'startdate': datetime(*list(map(int, anime.startdate.string.split("-")))),
        'enddate': datetime(*list(map(int, anime.enddate.string.split("-")))),
        'titles': [(
          str(title.string),
          title['type'] if 'type' in title else "unknown"
          ) for title in anime.find_all('title')],
        'title': str(titles.find('title', attrs={'type': "main"}).string),
        'relatedanime': [],
        'url': str(anime.url.string) if anime.url else None,
        'creators': anime.creators,
        'description': str(anime.description.string),
        'ratings': SmartDict({
          'permanent': float(anime.ratings.permanent.string),
          'temporary': float(anime.ratings.temporary.string),
          'review': float(anime.ratings.review.string) if anime.ratings.review else ''
          }),
        'picture': "http://img7.anidb.net/pics/anime/" + str(anime.picture.string),
        'tags': [(genre.string, genre.parent.get("weight")) for genre in anime.tags.find_all('name') if (genre.parent.name == "tag" and genre.parent.get("weight") != '0')],
        'characters': [],
        'episodes': [],

        })

        self._cache[id] = a

        return a


class SmartDict(dict):
    def __init__(self, *a, **kw):
        super(SmartDict, self).__init__(**kw)
        for x in a:
            try:
                self.update(x)
            except TypeError:
                self.update(x.__dict__)
        self.__dict__ = self


class Anime:
    def __init__(self, data={}, partial=False, **kw):
        self._data = data
        self._partial = partial
        if partial:
            self._updater = kw['updater']

    def _update(self):
        if not self._partial:
            raise Exception("Attempted to update a ready object")
        else:
            self._data = self._updater()._data
            self._partial = False

    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        else:
            if self._partial:
                self._update()
                if name in self._data:
                    return self._data[name]
                else:
                    raise AttributeError("no attribute called '%s'" % name)
            else:
                raise AttributeError("no attribute called '%s'" % name)

    def __repr__(self):
        return u'<Anime %i "%s">' % (self.id, self.title)
