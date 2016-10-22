import factory
from factory.django import DjangoModelFactory

from .models import Profile, Work, Category
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

class WorkFactory(DjangoModelFactory):
    class Meta:
        model = Work

    category = factory.Iterator(Category.objects.all())

    @factory.iterator
    def title():
        qs = Work.objects.values_list('title', flat=True).all()[:20]
        for title in qs:
            yield title

    nsfw = factory.Faker('boolean')
    synopsis = factory.Faker('text')


def create_user(**kwargs):
    return UserFactory.create(**kwargs)

def create_user_with_profile(**kwargs):
    profile = kwargs.pop('profile')
    user = create_user(**kwargs)
    for key, value in profile.items():
        setattr(user.profile, key, value)

    return user
