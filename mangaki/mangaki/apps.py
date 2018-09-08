from django.apps import AppConfig

from zero import RecommendationAlgorithm


class MangakiConfig(AppConfig):
    name = 'mangaki'
    verbose_name = 'Mangaki'

    def ready(self):
        # Ensure signal receivers decorated with `@receiver` are connected by
        # importing the `receivers` module.
        from . import receivers
        RecommendationAlgorithm.factory.initialize()
