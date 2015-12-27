from django.apps import AppConfig
from django.contrib import algoliasearch

class MangakiConfig(AppConfig):
    name = 'mangaki'

    def ready(self):
        Anime = self.get_model('Anime')
        Manga = self.get_model('Manga')
        algoliasearch.register(Anime)
        algoliasearch.register(Manga)
