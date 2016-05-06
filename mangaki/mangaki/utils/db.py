from mangaki.utils.mal import MAL


def refresh_poster(work):
    mal = MAL()
    mal.search(work.title)
    work.poster = mal.get_poster()
    work.save()
