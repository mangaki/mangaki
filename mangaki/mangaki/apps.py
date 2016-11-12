from django.apps import AppConfig


class MangakiConfig(AppConfig):
    name = 'mangaki'
    verbose_name = 'Mangaki'

    def ready(self):
        from . import receivers
