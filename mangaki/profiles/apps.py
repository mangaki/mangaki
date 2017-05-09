from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    name = 'profiles'
    verbose_name = 'Mangaki profiles'

    def ready(self):
        # Register receivers.
        # noinspection PyUnresolvedReferences
        import profiles.receivers

