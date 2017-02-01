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
      results.append(
        (int(anime['aid']),
        str(anime.find('title', attrs={'type': "official"}).string))
      )
    return results

  def get(self, id):
    """
    Allows retrieval of non-file or episode related information for a specific anime by AID (AniDB anime id).
    http://wiki.anidb.net/w/HTTP_API_Definition#Anime
    """
    id = int(id) # why?

    r = self._request("anime", {'aid': id})
    soup = BeautifulSoup(r.text.encode('utf-8'), 'xml')  # http://stackoverflow.com/questions/31126831/beautifulsoup-with-xml-fails-to-parse-full-unicode-strings#comment50430922_31146912
    with open('backup.xml', 'w') as f:
      f.write(r.text)
    if soup.error is not None:
      raise Exception(soup.error.string)

    anime = soup.anime
    all_titles = anime.titles
    # creators = anime.creators
    # episodes = anime.episodes
    # tags = anime.tags
    # characters = anime.characters
    # ratings = anime.ratings.{permanent, temporary}

    a = {
      'title': str(all_titles.find('title', attrs={'type': "main"}).string),
      'source': 'AniDB: ' + str(anime.url.string) if anime.url else None,
      'ext_poster': 'http://img7.anidb.net/pics/anime/' + str(anime.picture.string),
      # 'nsfw': ?
      'date': datetime(*list(map(int, anime.startdate.string.split("-")))),
      # not yet in model: 'enddate': datetime(*list(map(int, anime.enddate.string.split("-")))),
      'synopsis': str(anime.description.string),
      # 'artists': ? from anime.creators
      'nb_episodes': int(anime.episodecount.string),
      'anime_type': str(anime.type.string),
      'anidb_aid': id
    }
    return a
