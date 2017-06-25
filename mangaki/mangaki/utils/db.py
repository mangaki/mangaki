from typing import List
from urllib.parse import urlparse

from mangaki.models import Work
from mangaki.utils.mal import client


def get_potential_posters(work: Work) -> List[str]:
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
            'current': work.int_poster is None,
            'url': work.ext_poster
        })
    entry = client.get_entry_from_work(work)  # Ask MAL for guidance.
    if entry.poster is not None:
        path = urlparse(entry.poster).path
        if path not in ext_urls:
            ext_urls.add(entry.poster)
            posters.append({
                'current': False,
                'url': entry.poster,
            })
    return posters
