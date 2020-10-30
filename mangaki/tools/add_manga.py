from mangaki.models import Artist, Manga, Genre
from django.db.utils import IntegrityError, DataError
import re
from collections import Counter


def run():
    with open('../data/manga-news/manga.csv') as f:
        next(f)
        artists = {}
        Counter()
        for i, line in enumerate(f):
            # print(len(line.split(';;')))
            title, vo_title, writer, mangaka, editor, origin, genre1, genre2, manga_type, synopsis, poster = line.split(';;')
            for artist in [writer, mangaka]:
                if artist in artists:
                    continue
                m = re.match('^([A-ZÔÛÏ\'-]+) (.*)$', writer)
                if m:
                    last_name, first_name = m.groups()
                    last_name = last_name.lower().capitalize()
                if not m:
                    first_name = ''
                    last_name = artist
                if Artist.objects.filter(first_name=first_name, last_name=last_name).count() == 0:
                    a = Artist(first_name=first_name, last_name=last_name)
                    a.save()
                else:
                    a = Artist.objects.get(first_name=first_name, last_name=last_name)
                artists[artist] = a
    with open('../data/manga-news/manga.csv') as f:
        next(f)
        for i, line in enumerate(f):
            title, vo_title, writer, mangaka, editor, origin, genre1, genre2, manga_type, synopsis, poster = line.split(';;')
            try:
                if Manga.objects.filter(title=title, vo_title=vo_title).count() == 0:
                    manga = Manga(title=title, vo_title=vo_title, mangaka=artists[mangaka], writer=artists[writer], editor=editor, origin=origin.lower().replace('hong kong', 'hong-kong').replace('international', 'intl'), manga_type=manga_type.lower(), source='', poster=poster, synopsis=synopsis)
                    manga.save()
                else:
                    manga = Manga.objects.get(title=title, vo_title=vo_title)
                if genre1:
                    manga.genre.add(Genre.objects.get(title=genre1))
                if genre2:
                    manga.genre.add(Genre.objects.get(title=genre2))
            except IntegrityError as err:
                print(line)
                print(writer)
                print(err)
                break
            except DataError as err:
                print(line)
                print(origin)
                print(err)
                break
            except Genre.DoesNotExist as err:
                print(line)
                print('Genres: [%s] [%s]' % (genre1, genre2))
                print(err)
                break


run()
