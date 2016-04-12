from django.core.management.base import BaseCommand, CommandError
from mangaki.utils.anidb import AniDB
from mangaki.models import Artist, Role, Staff, Work, ArtistSpelling
from django.db.models import Count
from urllib.parse import urlparse, parse_qs
import sys


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


class Command(BaseCommand):
    args = ''
    help = 'Retrieve AniDB data'

    def add_arguments(self, parser):
        parser.add_argument('id', nargs='*', type=int)

    def handle(self, *args, **options):        
        category = 'anime'
        start = 0
        if options.get('id'):
            anime_id = options.get('id')[0]
            anime = Work.objects.filter(category__slug='anime').get(id=anime_id)
            if anime.anidb_aid == 0:
                for reference in anime.reference_set.all():
                    if reference.url.startswith('http://anidb.net') or reference.url.startswith('https://anidb.net'):
                        query = urlparse(reference.url).query
                        anidb_aid = parse_qs(query).get('aid')
                        if anidb_aid:
                            anime.anidb_aid = anidb_aid[0]
                            anime.save()
            todo = Work.objects.filter(category__slug='anime', id=anime_id, anidb_aid__gt=0)
        else:
            todo = Work.objects\
                .only('pk', 'title', 'poster', 'nsfw')\
                .annotate(rating_count=Count('rating'))\
                .filter(category__slug=category, rating_count__gte=6)\
                .exclude(anidb_aid=0)\
                .order_by('-rating_count')
        a = AniDB('mangakihttp', 1)
        i = 0
        for anime in todo:
            i += 1
            if i < start:
                continue
            print(i, ':', anime.title, anime.id)
            creators = a.get(anime.anidb_aid).creators
            print(creators)
            staff_map = dict(Role.objects.filter(slug__in=['author', 'director', 'composer']).values_list('slug', 'pk'))
            for creator in creators.findAll('name'):
                artist = get_or_create_artist(creator.string)
                if creator['type'] == 'Direction':
                    staff_id = 'director'
                elif creator['type'] == 'Music':
                    staff_id = 'composer'
                elif creator['type'] == 'Original Work' or creator['type'] == 'Story Composition':
                    staff_id = 'author'
                else:
                    staff_id = None
                if staff_id is not None:
                    Staff.objects.get_or_create(work=anime, role_id=staff_map[staff_id], artist=artist)
                anime.save()
