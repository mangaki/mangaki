import factory
from factory.django import DjangoModelFactory

from .models import Profile
from django.contrib.auth.models import User

class ProfileFactory(DjangoModelFactory):
    class Meta:
        model = Profile

    user = factory.SubFactory('mangaki.factories.UserFactory', profile=None)
    mal_username = factory.Faker('user_name')
    is_shared = factory.Faker('boolean')
    nsfw_ok = factory.Faker('boolean')
    newsletter_ok = factory.Faker('boolean')
    avatar_url = factory.LazyAttribute(lambda o: '{}{}.png'.format(factory.Faker('url').generate({}), o.mal_username))

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker('user_name')
    email = factory.LazyAttribute(lambda o: '{}@mangaki.fr'.format(o.username))
    profile = factory.RelatedFactory(ProfileFactory, 'user')

def create_user(**kwargs):
    return UserFactory.build(**kwargs)
