from mangaki.models import Artist, Anime, Genre, Studio, Editor
from django.db.utils import IntegrityError, DataError
import re
from collections import Counter, namedtuple


AnimeData = namedtuple('AnimeData', 'title vo_title studio author editor anime_type genre1 genre2 nb_episodes origin synopsis poster')


def create_if_not_exists(model, title):
    if model.objects.filter(title=title).count() > 0:
        return model.objects.get(title=title)
    print('Creating', model, title)
    obj = model(title=title)
    obj.save()
    return obj


def run():
    with open('../data/manga-news/anime.csv') as f:
        next(f)
        artists = {}
        anime_data = []
        for i, line in enumerate(f):
            title, vo_title, studio, author, editor, anime_type, genre1, genre2, nb_episodes, origin, synopsis, poster = line.split(';;')
            anime_data.append(AnimeData(*line.split(';;')))
    with open('../data/PAIR.log') as f:
        for line in f:
            mangaki_id = int(line.split('::')[0])
            mn_id = int(line.split('::')[1])
            anime = Anime.objects.get(id=mangaki_id)
            data = anime_data[mn_id - 1]
            anime.studio = create_if_not_exists(Studio, data.studio)
            anime.editor = create_if_not_exists(Editor, data.editor)
            m = re.match('^([A-ZÔÛÏ\'-]+) (.*)$', data.author)
            if m:
                last_name, first_name = m.groups()
                last_name = last_name.lower().capitalize()
            if not m:
                first_name = ''
                last_name = data.author
            if Artist.objects.filter(first_name=first_name, last_name=last_name).count() == 0:
                print('NEW')
                a = Artist(first_name=first_name, last_name=last_name)
                a.save()
            else:
                a = Artist.objects.get(first_name=first_name, last_name=last_name)
                print('Exists', a)
            anime.author = a
            anime.anime_type = data.anime_type
            genre1 = create_if_not_exists(Genre, data.genre1)
            genre2 = create_if_not_exists(Genre, data.genre2)
            anime.genre.add(genre1)
            anime.genre.add(genre2)
            anime.nb_episodes = data.nb_episodes
            anime.origin = data.origin
            anime.synopsis = data.synopsis  # The most important!
            anime.save()


run()
