from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from mangaki.models import Anime, Rating
from mangaki.utils.mal import lookup_mal_api
from mangaki.settings import BASE_DIR
from urllib.request import urlretrieve
import os

def merge_anime(ids):
    chosen_id = min(ids)
    anime = Anime.objects.get(id=chosen_id)
    if '/' in anime.source:
        mal_id = anime.source[anime.source.rindex('/') + 1:]
        old_poster = anime.poster
        new_poster = Anime.objects.get(id=max(ids)).poster
        if old_poster != new_poster:
            answer = input('Change poster as well? [y/n] ')
            if answer == 'y':
                urlretrieve(old_poster, os.path.join(BASE_DIR, 'mangaki/static/img/old/mal-%s.jpg' % mal_id))
                anime.poster = new_poster
                anime.save()
    for anime_id in ids:
        if anime_id != chosen_id:
            for rating in Rating.objects.filter(work__id=anime_id).select_related('user'):
                if Rating.objects.filter(user=rating.user, work__id=chosen_id).count() == 0:  # Has not yet rated the other one
                    rating.work = Anime.objects.get(id=chosen_id)
                    rating.save()
                else:
                    rating.delete()
            assert Anime.objects.get(id=anime_id).rating_set.count() == 0
            Anime.objects.filter(id=anime_id).delete()
            print('ID %d deleted' % anime_id)

class Command(BaseCommand):
    args = ''
    help = 'Finds duplicates'
    def handle(self, *args, **options):
        conflicts = set()
        for entry in Anime.objects.values('poster').annotate(Count('poster')).filter(poster__count__gte=2):  # Same poster
            ids = []
            for anime in Anime.objects.filter(poster=entry['poster']):
                ids.append(anime.id)
            conflicts.add(tuple(sorted(ids)))
        for entry in Anime.objects.values('title').annotate(Count('title')).filter(title__count__gte=2):  # Same title
            ids = []
            for anime in Anime.objects.filter(title=entry['title']):
                ids.append(anime.id)
            conflicts.add(tuple(sorted(ids)))
        for ids in conflicts:
            total_nb_ratings = 0
            sources = set(Anime.objects.get(id=anime_id).source for anime_id in ids)
            nb_sources = len(sources)
            id_of_poster = {}
            for anime_id in ids:
                anime = Anime.objects.get(id=anime_id)
                nb_ratings = len(anime.rating_set.all())
                print('%d : %s (%s)' % (anime_id, anime.title, anime.poster))
                print('%d l\'ont noté' % nb_ratings)
                total_nb_ratings += nb_ratings
                id_of_poster[anime.poster] = anime_id
            if nb_sources > 1:
                print('Bizarre, plusieurs sources :', sources)
                rename_tasks = []
                for entry in lookup_mal_api(Anime.objects.get(id=ids[0]).title):
                    poster = entry['image']
                    if poster in id_of_poster:
                        rename_tasks.append((id_of_poster[poster], entry['title']))
                    else:
                        print(entry['title'])
                for anime_id, proposed_title in rename_tasks:
                    print(anime_id, proposed_title)
                for anime_id, proposed_title in rename_tasks:
                    answer = input('=> Rename ID %d into %s? [y/n] ' % (anime_id, proposed_title))
                    if answer == 'y':
                        Anime.objects.filter(id=anime_id).update(title=proposed_title)
                    elif answer != 'n':
                        Anime.objects.filter(id=anime_id).update(title=answer)
                    else:
                        print('Okay, next.')
            if nb_sources == 1 and nb_ratings == 0:
                print('MERGE automatique')
                merge_anime(ids)
            elif nb_sources == 1:
                answer = input('=> Merge into %d? [y/n] ' % min(ids))
                if answer == 'y':
                    merge_anime(ids)
