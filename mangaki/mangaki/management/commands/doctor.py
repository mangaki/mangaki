import os
from heapq import heappop, heappush
from urllib.request import urlretrieve

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count

from mangaki.models import Rating, Work
from mangaki.utils.mal import client, MALWorks


def merge_anime(ids):
    print('merge', ids)
    chosen_id = min(ids)
    anime = Work.objects.get(id=chosen_id)
    if '/' in anime.source:
        mal_id = anime.source[anime.source.rindex('/') + 1:]
        old_poster = anime.ext_poster
        new_poster = Work.objects.get(id=max(ids)).ext_poster
        if old_poster != new_poster:
            answer = input('Change poster as well? [y/n] ')
            if answer == 'y':
                urlretrieve(old_poster, os.path.join(settings.BASE_DIR, 'mangaki/static/img/old/mal-%s.jpg' % mal_id))
                anime.ext_poster = new_poster
                anime.save()
    for anime_id in ids:
        if anime_id != chosen_id:
            for rating in Rating.objects.filter(work__id=anime_id).select_related('user'):
                if Rating.objects.filter(user=rating.user, work__id=chosen_id).count() == 0:  # Has not yet rated the other one
                    rating.work = Work.objects.get(id=chosen_id)
                    rating.save()
                else:
                    rating.delete()
            assert Work.objects.get(id=anime_id).rating_set.count() == 0
            Work.objects.filter(id=anime_id).delete()
            print('ID %d deleted' % anime_id)


class Command(BaseCommand):
    args = ''
    help = 'Finds duplicates'

    def handle(self, *args, **options):
        conflicts = []
        entries = {
            'ext_poster': Work.objects.filter(category__slug='anime').values_list('ext_poster').annotate(Count('ext_poster')).filter(ext_poster__count__gte=2),
            'title': Work.objects.filter(category__slug='anime').values_list('title').annotate(Count('title')).filter(title__count__gte=2)
        }
        for category in entries:
            print(len(entries[category]), category, 'conflicts')
            for entry, _ in entries[category]:
                ids = []
                priority = 0
                for anime in Work.objects.filter(category__slug='anime', **{category: entry}):
                    ids.append(anime.id)
                    priority += anime.rating_set.count()
                heappush(conflicts, (-priority, tuple(sorted(ids))))
        while conflicts:
            _, ids = heappop(conflicts)
            total_nb_ratings = 0
            sources = set(Work.objects.get(id=anime_id).source for anime_id in ids)
            nb_sources = len(sources)
            id_of_poster = {}
            nb_ratings = 0
            for anime_id in ids:
                anime = Work.objects.get(id=anime_id)
                nb_ratings = len(anime.rating_set.all())
                print('%d : %s (%s)' % (anime_id, anime.title, anime.ext_poster))
                print('%d l\'ont noté' % nb_ratings)
                total_nb_ratings += nb_ratings
                id_of_poster[anime.ext_poster] = anime_id
            if nb_sources > 1:
                print('Bizarre, plusieurs sources :', sources)
                rename_tasks = []
                first_work = Work.objects.get(id=ids[0])
                for entry in client.search_works(MALWorks(first_work.category.slug), first_work.title):
                    poster = entry.poster
                    if poster in id_of_poster:
                        rename_tasks.append((id_of_poster[poster], entry.english_title or entry.title))
                    else:
                        print(entry.english_title or entry.title)
                for anime_id, proposed_title in rename_tasks:
                    print(anime_id, proposed_title)
                for anime_id, proposed_title in rename_tasks:
                    answer = input('=> Rename ID %d into %s? [y/n] ' % (anime_id, proposed_title))
                    if answer == 'y':
                        Work.objects.filter(id=anime_id).update(title=proposed_title)
                    elif answer != 'n':
                        Work.objects.filter(id=anime_id).update(title=answer)
                    else:
                        print('Okay, next.')
            if nb_sources == 1 and nb_ratings == 0:
                print('MERGE automatique')
                merge_anime(ids)
            elif nb_sources == 1:
                answer = input('=> Merge into %d? [y/n] ' % min(ids))
                if answer == 'y':
                    merge_anime(ids)
