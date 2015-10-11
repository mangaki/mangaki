from django.core.management.base import BaseCommand, CommandError
from mangaki.utils.anidb import AniDB
from mangaki.models import Anime, Artist

def get_or_create_artist(name):
    last, first = name.split()
    try:
        if Artist.objects.filter(first_name=first, last_name=last).count():
            contestants = Artist.objects.filter(first_name=first, last_name=last)
            return Artist.objects.get(first_name=first, last_name=last)
        elif Artist.objects.filter(first_name=first).count():
            contestants = Artist.objects.filter(first_name=first)
            return Artist.objects.get(first_name=first)
        elif Artist.objects.filter(last_name=last).count():
            contestants = Artist.objects.filter(last_name=last)
            return Artist.objects.get(last_name=last)
    except:
        for i, artist in enumerate(contestants):
            print('%d: %s' % (i, artist))
        answer = int(input('Which one? '))
        if answer < len(contestants):
            return contestants[answer]
    artist = Artist(first_name=first, last_name=last)
    artist.save()
    return artist

def try_replace(anime, key, artist_name):
    print(key, ':', artist_name)
    artist = get_or_create_artist(artist_name)
    if getattr(anime, key) == artist:
        return
    answer = input('Remplacer %s par %s ? ' % (getattr(anime, key), artist))
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
        for anime in Anime.objects.raw(work_query.format(category=category, min_ratings=6, order_by='rating_count DESC')):
            print(anime.title, anime.id)
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
