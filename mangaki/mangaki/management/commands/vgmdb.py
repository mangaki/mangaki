from django.core.management.base import BaseCommand, CommandError
from mangaki.utils.vgmdb import VGMdb
from mangaki.models import Artist, Work, ArtistSpelling
from urllib.parse import urlparse, parse_qs


def get_or_create_artist(name):
    try:
        return Artist.objects.get(name=name)
    except Artist.DoesNotExist:
        pass
    try:
        return ArtistSpelling.objects.get(was=name).artist
    except ArtistSpelling.DoesNotExist:
        pass
    # FIXME consider trigram search to find similar artists in Artist, ArtistSpelling
    true_name = input('I don\'t now %s (yet). Link to another artist? Type their name: ' % name)
    artist, _ = Artist.objects.get_or_create(name=true_name)
    ArtistSpelling(was=name, artist=artist).save()
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
        album = Work.objects.filter(category__slug='album').get(id=album_id)
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
