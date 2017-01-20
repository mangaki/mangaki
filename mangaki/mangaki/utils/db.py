from mangaki.utils.mal import MAL
import requests
from urllib.parse import urlparse


def get_potential_posters(work, request):
    posters = []
    ext_urls = set()
    if work.int_poster:
        posters.append({
            'current': True,
            'url': work.int_poster.url,
        })
    if work.ext_poster:
        ext_urls.add(urlparse(work.ext_poster).path)
        posters.append({
            'current': False,
            'url': work.ext_poster
        })
    mal = MAL()
    mal.search(work.title)  # Query the poster to MAL from the title
    poster_url = mal.get_poster()
    if poster_url:
        path = urlparse(poster_url).path
        if path not in ext_urls:
            ext_urls.add(poster_url)
            posters.append({
                'current': False,
                'url': poster_url,
            })
    return posters
