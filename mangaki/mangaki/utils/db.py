from mangaki.utils.mal import MAL
from urllib.request import urlretrieve


def refresh_poster(work):
    found = False
    if not work.has_poster_on_disk():
        poster_url = work.poster
        try:  # Try to download the poster
            urlretrieve(poster_url, work.get_poster_path())
            found = True
        except:
            mal = MAL()
            mal.search(work.title)  # Query the poster to MAL from the title
            poster_url = mal.get_poster()
            if poster_url:  # If poster was found
                try:
                    urlretrieve(poster_url, work.get_poster_path())
                    found = True
                    work.poster = poster_url  # For posterity
                except:
                    print('=> 404 derechef', poster_url)
                    work.poster = ''
            work.save()
    return found
