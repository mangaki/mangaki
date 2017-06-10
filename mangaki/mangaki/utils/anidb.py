from datetime import datetime
from typing import Dict, Tuple, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from lazy_object_proxy.utils import cached_property

from mangaki.models import Language, Work, WorkTitle, Category, ExtLanguage


def to_python_datetime(mal_date):
    """
    Converts myAnimeList's XML date YYYY-MM-DD to Python datetime format.
    >>> to_python_datetime('2015-07-14')
    datetime.datetime(2015, 7, 14, 0, 0)
    """
    return datetime(*list(map(int, mal_date.split("-"))))


class AniDB:
    BASE_URL = "http://api.anidb.net:9001/httpapi"
    SEARCH_URL = "http://anisearch.outrance.pl/"
    PROTOCOL_VERSION = 1

    def __init__(self, client_id, client_ver=0):
        self.client_id = client_id
        self.client_ver = client_ver
        self._cache = {}

    def _request(self, datapage, params=None):
        if params is None:
            params = {}

        params.update({
            'client': self.client_id,
            'clientver': self.client_ver,
            'protover': self.PROTOCOL_VERSION,
            'request': datapage
        })

        r = requests.get(self.BASE_URL, params=params)
        r.raise_for_status()
        return r

    # Anime http://wiki.anidb.net/w/HTTP_API_Definition#Access

    def search(self, q):
        """
        Search for `aid`s by anime title using service provided by eloyard.
        http://anisearch.outrance.pl/doc.html
        """
        r = requests.get(self.SEARCH_URL, params={
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

    def get_dict(self, anidb_aid):
        """
        Allows retrieval of non-file or episode related information for a specific anime by AID (AniDB anime id).
        Unlike get, this version can directly be converted to a Work object in Mangaki.
        """
        anidb_aid = int(anidb_aid)

        r = self._request("anime", {'aid': anidb_aid})
        soup = BeautifulSoup(r.text.encode('utf-8'),
                             'xml')  # http://stackoverflow.com/questions/31126831/beautifulsoup-with-xml-fails-to-parse-full-unicode-strings#comment50430922_31146912
        if soup.error is not None:
            raise Exception(soup.error.string)

        anime = soup.anime
        all_titles = anime.titles
        # creators = anime.creators # TODO
        # episodes = anime.episodes
        # tags = anime.tags
        # characters = anime.characters
        # ratings = anime.ratings.{permanent, temporary}

        main_title = None
        synonyms = {}
        titles = {}
        for title_node in all_titles.find_all('title'):
            title = str(title_node.string).strip()
            lang = title_node.get('xml:lang')
            title_type = title_node.get('type')
            titles[lang] = {
                'title': title,
                'type': title_type
            }

            if title_type == 'main':
                main_title = title

            if title_type == 'synonym':
                synonyms[lang] = title

        anime_dict = {
            'work_titles': {
                'main_title': main_title,
                'titles': titles,
            },
            'work': {
                'title': main_title,
                'source': 'AniDB: ' + str(anime.url.string) if anime.url else None,
                'ext_poster': urljoin('http://img7.anidb.net/pics/anime/', str(anime.picture.string)),
                # 'nsfw': ?
                'date': to_python_datetime(anime.startdate.string),
                # not yet in model: 'enddate': to_python_datetime(anime.enddate.string),
                'synopsis': str(anime.description.string),
                # 'artists': ? from anime.creators
                'nb_episodes': int(anime.episodecount.string),
                'anime_type': str(anime.type.string),
                'anidb_aid': anidb_aid
            }
        }

        return anime_dict

    @cached_property
    def anime_cat(self) -> Category:
        return Category.objects.get(slug='anime')

    @cached_property
    def lang_map(self) -> Dict[str, ExtLanguage]:
        ext_langs = (
            ExtLanguage.objects.filter(source='anidb')
            .select_related('lang').all()
        )

        return {
            ext.lang.code: ext for ext in ext_langs
        }

    def get_mangaki_work(self,
                         anidb_aid: int,
                         reload_lang_cache: bool = False) -> Tuple[Work, List[WorkTitle]]:
        """
        Use `get_dict` internally to create the bunch of objects you need to create a work.

        Cache internally intermediate models objects (e.g. Language, ExtLanguage, Category)

        :param anidb_aid: the AniDB identifier
        :type anidb_aid: integer
        :param reload_lang_cache: forcefully reload the ExtLanguage cache,
            if it has changed since the instantiation of the AniDB client (default: false).
        :type reload_lang_cache: boolean
        :return: the set of `Work`-related objects linked to the `anidb_aid` passed in parameter (e.g. Work, list of WorkTitle)
        :rtype: A tuple composed of a `mangaki.models.Work` instance and a list of `mangaki.models.WorkTitle`
        (in this order.)
        """
        data = self.get_dict(anidb_aid)

        work = Work(category=self.anime_cat, **data['work'])
        titles = data['work_titles']['titles']
        if reload_lang_cache:
            # Re-compute `lang_map`.
            delattr(self, 'lang_map')
            getattr(self, 'lang_map')

        work_titles = []
        for lang, title_data in titles.items():
            ext_lang_model = self.lang_map.get(lang)
            if ext_lang_model:
                work_titles.append(
                    WorkTitle(
                        work=work,
                        title=title_data['title'],
                        language=ext_lang_model.lang,  # Use the Language model and not the ExtLanguage!
                        type=title_data['type']
                    )
                )

        return work, work_titles

    def get(self, id):
        """
        Allows retrieval of non-file or episode related information for a specific anime by AID (AniDB anime id).
        http://wiki.anidb.net/w/HTTP_API_Definition#Anime
        """
        id = int(id)  # why?

        r = self._request("anime", {'aid': id})
        soup = BeautifulSoup(r.text.encode('utf-8'),
                             'xml')  # http://stackoverflow.com/questions/31126831/beautifulsoup-with-xml-fails-to-parse-full-unicode-strings#comment50430922_31146912

        if soup.error is not None:
            raise Exception(soup.error.string)

        anime = soup.anime
        titles = anime.titles
        ext_langs = ExtLanguage.objects.filter(source='anidb').all()
        languages = {ext_lang.ext_lang: ext_lang.lang.code for ext_lang in ext_langs}
        a = Anime({
            'id': id,
            'worktitles': [(title.string, title['type'], languages[title['xml:lang']])
                           for title in titles.find_all('title')
                           if title['type'] != 'short' and title['xml:lang'] in languages],
            'type': str(anime.type.string),
            'episodecount': int(anime.episodecount.string),
            'startdate': to_python_datetime(anime.startdate.string),
            'enddate': to_python_datetime(anime.enddate.string),
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
            'tags': [(genre.string, genre.parent.get("weight")) for genre in anime.tags.find_all('name') if
                     (genre.parent.name == "tag" and genre.parent.get("weight") != '0')],
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
    def __init__(self, data=None, partial=False, **kw):
        self._data = data or {}
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


if __name__ == "__main__":
    import doctest

    doctest.testmod()
