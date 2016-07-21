from django.core.management.base import BaseCommand, CommandError
from mangaki.utils.anidb import AniDB
from mangaki.models import Artist, Role, Staff, Work, WorkTitle, ArtistSpelling
from django.db.models import Count
from urllib.parse import urlparse, parse_qs
import sys

"""
Essayer sur des animes ayant sûrement des tags similaires ou alors en save 1 ds un fichier puis modifier
"""


def get_or_create_artist(name):
    try:
        return Artist.objects.get(name=name)
    except Artist.DoesNotExist:
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
        #all_worktitles = []
        
        for anime in todo:
            i += 1
            if i < start:
                continue
            print(i, ':', anime.title, anime.id)
            """
            anime=a.get(anime.anidb_aid).anime
            anime=str(anime)
            #tag = a.get(anime.anidb_aid).tag
            #tag = str(tag)
            
            my_file = open("/home/voisin/anidb.xml", "r+")
            
            my_file.write(anime)
            my_file.close()
            """

        
            #creators = a.get(anime.anidb_aid).creators
            #worktitles = a.get(anime.anidb_aid).worktitles
            #is_hentai = a.get(anime.anidb_aid).is_hentai
            #categories = a.get(anime.anidb_aid).categories
            tags = a.get(anime.anidb_aid).tags
            #print(worktitles)
            #print(is_hentai)
            #print(categories)
            #if is_hentai == "true" :
            #    anime.nsfw = True

            """
            print(creators)
            print(worktitles)
            """
            print(tags)
            #all_worktitles.append(worktitles)

            
            #for i in range(len(worktitles)):
            #    WorkTitle.objects.get_or_create(work=anime, title=worktitles[i][0], language=worktitles[i][2], specific_type=worktitles[i][1])
            

            #anime.save()
            
            for tag in tags:
                


            """
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
            """