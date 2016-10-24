import requests
from bs4 import BeautifulSoup

from datetime import datetime

BASE_URL = "http://api.anidb.net:9001/httpapi"
SEARCH_URL = "http://anisearch.outrance.pl/"
PROTOCOL_VERSION = 1

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
        print (params)
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
            picture = anime.find('picture')
            results.append(Anime({
                'id': int(anime['aid']),
                'title': str(anime.find('title', attrs={'type': "official"}).string),
                'picture': "http://img7.anidb.net/pics/anime/{}".format(picture.string) if picture is not None else None,
            }, partial=True, updater=lambda: self.get(anime.id)))

        return results

    def get(self, id):
        """
        Allows retrieval of non-file or episode related information for a specific anime by AID (AniDB anime id).
        http://wiki.anidb.net/w/HTTP_API_Definition#Anime
        """
        id = int(id) # why?

        r = self._request("anime", {'aid': id})
        soup = BeautifulSoup(r.text.encode('utf-8'), 'xml')  # http://stackoverflow.com/questions/31126831/beautifulsoup-with-xml-fails-to-parse-full-unicode-strings#comment50430922_31146912
        if soup.error is not None:
            raise Exception(soup.error.string)

        anime = soup.anime
        titles = anime.titles

        a = Anime({
            'id': id,
            'type': str(anime.type.string),
            'episodecount': int(anime.episodecount.string),
            'startdate': datetime(*list(map(int, anime.startdate.string.split("-")))),
            'enddate': datetime(*list(map(int, anime.enddate.string.split("-")))),
            'titles': [{
                'title': str(title.string),
                'lang': title['xml:lang'],
                'type': title['type'] if 'type' in title else None
            }
                for title in anime.titles.find_all('title')
            ],
            'title': str(titles.find('title', attrs={'type': "main"}).string),
            'relatedanime': [{
                'title': str(relanime.string),
                'id': int(relanime['id']),
                'type': relanime['type'] if 'type' in relanime else None
            }
                for relanime in anime.relatedanime.find_all('anime')
            ] if anime.relatedanime is not None else [],
            'url': str(anime.url.string) if anime.url else None,
            'creators': [
                {
                    'full_name': str(creator.string),
                    'type': creator['type'] if 'type' in creator else None,
                    'id': int(creator['id'])
                }
                for creator in anime.creators.find_all('name')
            ],
            'description': str(anime.description.string),
            'ratings': SmartDict({
                'permanent': float(anime.ratings.permanent.string),
                'temporary': float(anime.ratings.temporary.string),
                'review': float(anime.ratings.review.string) if anime.ratings.review else ''
            }),
            'picture': "http://img7.anidb.net/pics/anime/" + str(anime.picture.string),
            'categories': [],
            'tags': [
                {
                    'globalspoiler': bool(tag['globalspoiler']),
                    'id': int(tag['id']),
                    'localspoiler': bool(tag['localspoiler']),
                    'parentid': int(tag['parentid']),
                    'update': datetime(*list(map(int, tag['update'].split('-')))),
                    'verified': bool(tag['verified']),
                    'weight': int(tag['weight']),
                    'name': str(tag.find('name').string),
                    'description': str(tag.find('description').string)
                }
                for tag in anime.tag.find_all('tag')
            ] if anime.tag is not None else [],
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
