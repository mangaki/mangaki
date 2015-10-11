from django.core.management.base import BaseCommand, CommandError
from mangaki.utils.anidb import AniDB
from mangaki.models import Anime, Artist
import sys

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
    help = 'Retrieve AniDB data'

    def handle(self, *args, **options):
        category = 'anime';
        work_query = 'SELECT mangaki_{category}.work_ptr_id, mangaki_work.id, mangaki_work.title, mangaki_work.poster, mangaki_work.nsfw, COUNT(mangaki_work.id) rating_count FROM mangaki_{category}, mangaki_work, mangaki_rating WHERE mangaki_{category}.work_ptr_id = mangaki_work.id AND mangaki_rating.work_id = mangaki_work.id AND mangaki_{category}.anidb_aid > 0 GROUP BY mangaki_work.id, mangaki_{category}.work_ptr_id HAVING COUNT(mangaki_work.id) >= {min_ratings} ORDER BY {order_by}'
        a = AniDB('mangakihttp', 1)
        start = int(sys.argv[2]) if len(sys.argv) > 2 else 0  # Skipping
        i = 0
        for anime in Anime.objects.raw(work_query.format(category=category, min_ratings=6, order_by='rating_count DESC')):
            i += 1
            if i <= start:
                continue
            print(i, ':', anime.title, anime.id)
            creators = a.get(anime.anidb_aid).creators
            print(creators)
            for creator in creators.findAll('name'):
                if creator['type'] == 'Director':
                    try_replace(anime, 'director', creator.string)
                elif creator['type'] == 'Music':
                    try_replace(anime, 'composer', creator.string)
                elif creator['type'] == 'Original Work':
                    try_replace(anime, 'author', creator.string)
                anime.save()
