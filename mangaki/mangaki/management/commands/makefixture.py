from django.core.management.base import BaseCommand, CommandError
from mangaki.models import Anime, Artist, Studio, Editor, Genre
from django.core import serializers


class Command(BaseCommand):
    args = ''
    help = 'Make fixture of Anime objects'

    def add_arguments(self, parser):
        parser.add_argument('id', nargs='+', type=int)

    def handle(self, *args, **options):        
        category = 'anime'

        ids = options.get('id')
        bundle = []
        for anime_id in ids:
            anime = Anime.objects.filter(id=anime_id).select_related('director', 'composer', 'author', 'studio', 'editor').prefetch_related('genre')[0]
            bundle.extend([anime, anime.director, anime.composer, anime.author, anime.studio, anime.editor] + list(anime.genre.all()))        
        data = serializers.serialize('json', bundle)
        print(data)
