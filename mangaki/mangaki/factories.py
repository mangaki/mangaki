import factory
from factory.django import DjangoModelFactory

from .models import Work, Category


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

