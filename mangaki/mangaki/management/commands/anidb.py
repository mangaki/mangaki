from django.core.management.base import BaseCommand, CommandError
from mangaki.utils.anidb import AniDB
from mangaki.models import Artist, Tag, TaggedWork, Role, Staff, Work, WorkTitle, ArtistSpelling
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
        

        i = 0
        
        
        for anime in todo:
            i += 1
            if i < start:
                continue
            print(i, ':', anime.title, anime.id)
            """
            my_file = open("/home/voisin/anidb2.xml", "r+")
            
            my_file.write(anime)
            my_file.close()
            """

            #creators = a.get(anime.anidb_aid).creators
            #worktitles = a.get(anime.anidb_aid).worktitles
            #print(worktitles)
            
            
            

            #for i in range(len(worktitles)):
            #    WorkTitle.objects.get_or_create(work=anime, title=worktitles[i][0], language=worktitles[i][2], specific_type=worktitles[i][1])
            

            #anime.save()
            deleted_tags, added_tags, updated_tags, kept_tags = anime.retrieve_tags()
           
            print(anime.title+":")
            if deleted_tags != {} :
                print("\n\tLes tags enlevés sont :")
                for tag, weight in deleted_tags.items():
                     print('\t\t{}: {} '.format(tag, weight))

            if added_tags != {}:
                print("\n\tLes tags totalement nouveaux sont :")
                for tag, weight in added_tags.items():
                    print('\t\t{}: {} '.format(tag, weight))
    
            if updated_tags != {}:
                print("\n\tLes tags modifiés sont :")
                for tag, weight in updated_tags.items():
                    print('\t\t{}: {} -> {}'.format(tag, weight[0], weight[1]))  
  
            if kept_tags != {}:
                print("\n\tLes tags non modifiés/restés identiques sont :")
                for tag, weight in kept_tags.items():
                    print('\t\t{}: {} '.format(tag, weight))

    

            choice  = input("Voulez-vous réaliser ces changements [y/n] : ")
            if choice == 'n':
                print("\nOk, aucun changement ne va être fait")
            elif choice =='y' :
    
                for  title, weight in added_tags.items():
                    current_tag = Tag.objects.update_or_create(title=title)[0]
                    TaggedWork(tag=current_tag, work=anime, weight=weight).save()
                for title, weight in updated_tags:
                    current_tag = Tag.objects.filter(title=title)[0]
                    tag_work = TaggedWork.objects.get(tag=current_tag, work=anime, weight=weight[0])
                    tag_work.delete()
                    TaggedWork(tag=current_tag, work=anime, weight=weight[1]).save()
        
                for title, weight in deleted_tags.items():
                    current_tag = Tag.objects.get(title=title)
                    TaggedWork.objects.get(tag=current_tag, work=anime, weight=weight).delete()
            


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