from django.core.management.base import BaseCommand, CommandError
from mangaki.utils.anidb import AniDB
from mangaki.models import Anime, Artist, Role, Staff
from urllib.parse import urlparse, parse_qs
import sys

def pick_among(name, contestants):
    for i, artist in enumerate(contestants):
        print('%d: %s' % (i, artist))
    answer = int(input('Who is {}? '.format(name)))
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
        choice = pick_among(name, contestants)
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
    help = 'Retrieve AniDB data'

    def add_arguments(self, parser):
        parser.add_argument('id', nargs='+', type=int)

    def handle(self, *args, **options):        
        category = 'anime'
        start = 0
        if options.get('id'):
            anime_id = options.get('id')[0]
            anime = Anime.objects.get(id=anime_id)
            if anime.anidb_aid == 0:
                for reference in anime.reference_set.all():
                    if reference.url.startswith('http://anidb.net') or reference.url.startswith('https://anidb.net'):
                        query = urlparse(reference.url).query
                        anidb_aid = parse_qs(query).get('aid')
                        if anidb_aid:
                            anime.anidb_aid = anidb_aid[0]
                            anime.save()
            todo = Anime.objects.filter(id=anime_id, anidb_aid__gt=0)
        else:
            work_query = 'SELECT mangaki_{category}.work_ptr_id, mangaki_work.id, mangaki_work.title, mangaki_work.poster, mangaki_work.nsfw, COUNT(mangaki_work.id) rating_count FROM mangaki_{category}, mangaki_work, mangaki_rating WHERE mangaki_{category}.work_ptr_id = mangaki_work.id AND mangaki_rating.work_id = mangaki_work.id AND mangaki_work.anidb_aid > 0 GROUP BY mangaki_work.id, mangaki_{category}.work_ptr_id HAVING COUNT(mangaki_work.id) >= {min_ratings} ORDER BY {order_by}'
            todo = Anime.objects.raw(work_query.format(category=category, min_ratings=6, order_by='rating_count DESC'))
            """if sys.argv[2] == 'from':
                start = int(sys.argv[3])"""
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
