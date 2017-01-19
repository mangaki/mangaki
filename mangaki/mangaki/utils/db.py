from mangaki.utils.mal import MAL
from django.contrib.sites.models import Site
from urllib.request import urlretrieve
import requests


def get_potential_posters(work, request):
    posters = []
    if work.has_poster_on_disk():
        posters.append('%s://%s%s' % (request.scheme, Site.objects.get_current().domain, work.safe_poster(request.user)))
    if work.poster:
        posters.append(work.poster)
    mal = MAL()
    mal.search(work.title)  # Query the poster to MAL from the title
    poster_url = mal.get_poster()
    if poster_url:
        posters.append(poster_url)
    return filter(lambda url: requests.get(url).status_code == 200, posters)


def retrieve_poster(work, poster_url):
    try:
        urlretrieve(poster_url, work.get_poster_path())
        work.poster = ''
        work.save()
        return work.title
    except:
        pass
