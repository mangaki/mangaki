from urllib.parse import urlparse

from mangaki.utils.mal import client


def get_potential_posters(work):
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
    work = client.search_work(work.title)  # Query the poster to MAL from the title
    if work.poster_url:
        path = urlparse(work.poster_url).path
        if path not in ext_urls:
            ext_urls.add(work.poster_url)
            posters.append({
                'current': False,
                'url': work.poster_url,
            })
    return posters
