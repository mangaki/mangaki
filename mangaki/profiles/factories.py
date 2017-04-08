from django.conf import settings
from django.db.models.signals import post_save
from factory import DjangoModelFactory
from factory.django import mute_signals
import factory

from profiles.models import Profile


class ProfileFactory(DjangoModelFactory):
    class Meta:
        model = Profile

    user = factory.SubFactory('mangaki.factories.UserFactory', profile=None)
    mal_username = factory.Faker('user_name')
    is_shared = factory.Faker('boolean')
    nsfw_ok = factory.Faker('boolean')
    newsletter_ok = factory.Faker('boolean')
    avatar_url = factory.LazyAttribute(lambda o: '{}{}.png'.format(factory.Faker('url').generate({}), o.mal_username))


@mute_signals(post_save)
class UserFactory(DjangoModelFactory):
    class Meta:
        model = settings.AUTH_USER_MODEL

    username = factory.Faker('user_name')
    email = factory.LazyAttribute(lambda o: '{}@mangaki.fr'.format(o.username))
    profile = factory.RelatedFactory(ProfileFactory, 'user')


def create_user(**kwargs):
    return UserFactory.create(**kwargs)


def create_user_with_profile(**kwargs):
    profile = kwargs.pop('profile')
    user = create_user(**kwargs)
    for key, value in profile.items():
        setattr(user.profile, key, value)

    return user
