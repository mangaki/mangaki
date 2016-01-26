from django.core.management.base import BaseCommand, CommandError
from mangaki.utils.vgmdb import VGMdb
from mangaki.models import Anime, Artist, Album
from urllib.parse import urlparse, parse_qs

def pick_among(contestants):
    for i, artist in enumerate(contestants):
        print('%d: %s' % (i, artist))
    answer = int(input('Which one? '))
    if answer < len(contestants):
        return contestants[answer]

def get_or_create_artist(name):
    if ' ' in name:
        parts = name.split()
        if len(parts) == 2:
            last, first = parts
        else:
            last, first = parts[-1], ' '.join(parts[:-1])  # Diana Wynne Jones
    else:
        last, first = name, ''
    try:
        contestants = []
        if Artist.objects.filter(first_name=first, last_name=last).count():
            contestants = Artist.objects.filter(first_name=first, last_name=last)
            return Artist.objects.get(first_name=first, last_name=last)
        elif first != '' and Artist.objects.filter(first_name=first).count():
            contestants = Artist.objects.filter(first_name=first)
        elif Artist.objects.filter(last_name=last).count():
            contestants = Artist.objects.filter(last_name=last)
    except:
        pass
    if contestants:
        choice = pick_among(contestants)
        if choice:
            return choice
    artist = Artist(first_name=first, last_name=last)
    artist.save()
    return artist

def try_replace(anime, key, artist_name):
    print(key, ':', artist_name)
    artist = get_or_create_artist(artist_name)
    if getattr(anime, key) == artist:
        return
    answer = input('Remplacer %s par %s ? ' % (getattr(anime, key), artist)) if getattr(anime, key).id != 1 else 'y'
    if answer == 'y':
        setattr(anime, key, artist)
        anime.save()

class Command(BaseCommand):
    args = ''
    help = 'Retrieve VGMdb data'

    def add_arguments(self, parser):
        parser.add_argument('id', nargs='+', type=int)

    def handle(self, *args, **options):        
        category = 'anime'

        album_id = options.get('id')[0]
        album = Album.objects.get(id=album_id)
        if album.vgmdb_aid:
            vgmdb = VGMdb()
            print(album.title, album.id)
            vgmdb_album = vgmdb.get(album.vgmdb_aid)
            print(vgmdb_album)
            album.title = vgmdb_album.title
            album.poster = vgmdb_album.poster
            album.date = vgmdb_album.date
            album.catalog_number = vgmdb_album.catalog_number
            try_replace(album, 'composer', vgmdb_album.composers[0][0])
            # print(album.__dict__)
            album.save()
