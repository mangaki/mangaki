from django.core.management.base import BaseCommand, CommandError
from mangaki.models import Artist, Anime, Genre
from django.db.models import Count
from django.db.utils import IntegrityError, DataError
import re
from collections import Counter, OrderedDict

def get_slug(name, trim=False):
    pre = OrderedDict([('l\'', '')])
    replacements = OrderedDict([('ō', 'ou'), ('ū', 'uu'), ('é', 'e'), ('è', 'e'), ('ê', 'e'), ('à', 'a'), ('â', 'a'), ('î', 'i'), ('ç', 'c'), ('λ', 'lambda'), (r'(★|☆|/)', '-'), (r'[^a-z0-9- ]', ''), (' ', '-'), (r'-+', '-'), ('^-', ''), ('-$', '')])  # Last update 08/06/2015
    post = OrderedDict([('^the-', ''), ('^le-', ''), ('^les-', ''), ('^la-', '')])

    slug = name.lower()
    if trim:
        for token in pre:
            slug = re.sub(token, pre[token], slug)    
    for token in replacements:
        slug = re.sub(token, replacements[token], slug)
    if trim:
        for token in post:
            slug = re.sub(token, post[token], slug)    
    return slug


def save_log(filename, line):
    with open('../data/%s.log' % filename, 'a') as f:
        f.write(line + '\n')


def run():
    with open('../data/manga-news/anime.csv') as f:
        next(f)
        artists = {}
        synopsis_of = {}
        hipsters = Counter()
        mangaki_slugs = set()
        db_slugs = []
        for anime in Anime.objects.all():
            mangaki_slugs.add(get_slug(anime.title))
        for i, line in enumerate(f):
            # print(len(line.split(';;')))
            title, vo_title, studio, author, editor, anime_type, genre1, genre2, nb_episodes, origin, synopsis, poster = line.split(';;')
            slug = get_slug(title)
            db_slugs.append(slug)
            synopsis_of[slug] = synopsis

    ignored_ids = []
    with open('../data/IGNORE.log') as f:
        for line in f:
            ignored_ids.append(int(line.split('::')[0]))

    todo = list(Anime.objects.filter(synopsis='').exclude(id__in=ignored_ids)
                     .annotate(Count('rating')).order_by('-rating__count')[:10])[::-1]
    while todo:
        anime = todo.pop()
        print(anime.title, anime.rating__count)
        slug = get_slug(anime.title, trim=True)
        options = []
        for db_slug in db_slugs:
            if slug in db_slug:
                options.append((db_slug, synopsis_of[db_slug]))
            if 'Lelouch' in db_slug:
                print(slug, db_slug)

        if not options:
            print('Not found', anime.title)
            suggestion = input('Rename? ')
            if suggestion == 'q':
                break
            elif suggestion != 'n':
                save_log('RENAME', '%s::%s' % (anime.title, suggestion))
                anime.title = suggestion
                anime.save()
                todo.append(anime)
            else:
                db_id = int(input('Try anyway a certain ID? '))
                if db_id > 0:
                    db_slug = db_slugs[db_id - 1]
                    options.append((db_slug, synopsis_of[db_slug]))
                else:
                    save_log('IGNORE', '%s::%s' % (anime.id, anime.title))

        if options:
            if len(options) > 1:  # Several option
                for i, (slug, synopsis) in enumerate(options):
                    print(i + 1, ':', slug)
                option_id = input('Which one? ')
            else:  # Only one option, automatically chosen
                option_id = 1

            if 1 <= int(option_id) <= len(options):
                slug, synopsis = options[int(option_id) - 1]
                print('For %s (ID: %d), okay for: “%s”?' % (anime.title, anime.id, synopsis))
                if input() == 'y':
                    anime.synopsis = synopsis
                    anime.save()
                    save_log('PAIR', '%d::%d::%s::%s' % (anime.id, 1 + db_slugs.index(slug), anime.title, slug))


class Command(BaseCommand):
    args = ''
    help = 'Join Mangaki and Manga-News anime'
    def handle(self, *args, **options):
        run()
        # print(get_slug('L\'Attaque des titans'))
