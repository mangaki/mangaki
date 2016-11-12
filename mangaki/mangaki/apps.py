from django.apps import AppConfig


class MangakiConfig(AppConfig):
    name = 'mangaki'
    verbose_name = 'Mangaki'

    def ready(self):
        # Ensure signal receivers decorated with `@receiver` are connected by
        # importing the `receivers` module.
        from . import receivers
