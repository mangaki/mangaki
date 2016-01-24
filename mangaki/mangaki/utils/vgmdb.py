import requests
import json

from datetime import datetime

from urllib.request import urlopen

BASE_URL = "http://vgmdb.info/"
SITE_URL = "http://vgmdb.net/"
PROTOCOL_VERSION = 1

try:
  str = unicode
except:
  pass
  # str = str

class VGMdb:
  def __init__(self):
    self._cache = {}

  def get(self, id):
    """
    Allows retrieval of non-file or episode related information for a specific anime by AID (AniDB anime id).
    http://vgmdb.info/
    """
    id = int(id) # why?

    r = urlopen(BASE_URL + 'album/' + str(id) + '?format=json')
    soup = json.loads(r.read().decode('utf-8'))
    
    a = Album({
      'date': soup['release_date'],
      'composers': [(composer['names']['en'],
      ) for composer in soup['composers']],
      'title': soup['name'],
      'poster': soup['picture_full'],
      'vgmdb_aid': id,
      'catalog_number': soup['catalog'],
    })

    self._cache[id] = a

    return a

class Album:
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
    return u'<Album %i "%s">' % (self.vgmdb_aid, self.title)
