from django.core.management.base import BaseCommand

from mangaki.models import Artist, ArtistSpelling, Work, Role, Staff
from mangaki.utils.vgmdb import VGMdb
import logging


def get_or_create_artist(name):
    try:
        return Artist.objects.filter(name__unaccent=name)[0]
    except BaseException:
        pass
    try:
        return ArtistSpelling.objects.select_related('artist').get(was=name).artist
    except ArtistSpelling.DoesNotExist:
        pass
    # FIXME consider trigram search to find similar artists in Artist, ArtistSpelling
    true_name = input('I don\'t now %s (yet). Link to another artist? Type their name: ' % name)
    artist, _ = Artist.objects.get_or_create(name=true_name)
    ArtistSpelling(was=name, artist=artist).save()
    return artist


def add_to_staff(album, role_slug, artist_name):
    logging.info('%s: %s', role_slug, artist_name)
    artist = get_or_create_artist(artist_name)
    current_composer_ids = album.staff_set.filter(role__slug=role_slug).values_list('artist_id', flat=True)
    if artist.id not in current_composer_ids:
        Staff(work=album, artist=artist, role=Role.objects.get(slug=role_slug)).save()
        return artist


class Command(BaseCommand):
    args = ''
    help = 'Retrieve VGMdb data'

    def add_arguments(self, parser):
        parser.add_argument('id', nargs='+', type=int)

    def handle(self, *args, **options):
        album_id = options.get('id')[0]
        album = Work.objects.filter(category__slug='album').get(id=album_id)
        if album.vgmdb_aid:
            vgmdb = VGMdb()
            logging.info('%s %s', album.title, album.id)
            vgmdb_album = vgmdb.get(album.vgmdb_aid)
            logging.info(vgmdb_album)
            album.title = vgmdb_album.title
            album.ext_poster = vgmdb_album.poster
            album.date = vgmdb_album.date
            album.catalog_number = vgmdb_album.catalog_number
            artist = add_to_staff(album, 'composer', vgmdb_album.composers[0][0])
            if artist:
                self.stdout.write(self.style.SUCCESS('Successfully added %s to %s' % (artist, album.title)))
            album.save()
