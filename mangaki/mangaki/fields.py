from django.db import models

from mangaki.choices import Category, CATEGORY_CHOICES

class CategoryDescriptor:
    """
    A wrapper class that represents a category field on a model. This class
    handles proper conversions when getting/setting the `.category` field
    (*not* `category_id`).

    Heavily inspired by Django's related_descriptors.
    """

    def __init__(self, field):
        self.field = field

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        cat_id = getattr(instance, self.field.attname)

        if cat_id is None:
            return cat_id

        return Category(cat_id)

    def __set__(self, instance, value):
        if not isinstance(value, Category):
            value = Category(value)

        setattr(instance, self.field.attname, int(value))

# See Django custom fields documentation at
# https://docs.djangoproject.com/en/1.9/howto/custom-model-fields/j
class CategoryField(models.IntegerField):
    """
    A custom field that handles automatically conversion between an integer
    (stored in the database) and a convenient Category object.

    This field handles conversion from integer, strings, and Category objects,
    allowing the following kind of patterns:

        Work.objects.filter(category=1)
        Work.objects.filter(category='anime')
        Work.objects.last().category.slug # 'anime', 'manga', etc.
        str(Work.objects.last().category) # 'Anime', 'Manga', etc.

    **This field is actually the category_id field, and thus behaves like an
    IntegerField. Most type-casting stuff happens in the CategoryDescriptor.**
    """

    description = "A work category"

    def __init__(self, *args, **kwargs):
        kwargs['choices'] = CATEGORY_CHOICES
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['choices']
        return name, path, args, kwargs

    # Convert value from Python to SQL when performing a query. We let the
    # IntegerField do the conversion to int.
    def get_prep_value(self, value):
        if isinstance(value, str):
            value = Category(value)

        return super().get_prep_value(value)

    # Prepare values when performing a database lookup. We only handle 'exact'
    # (category=value) and 'in' (category__in=[value, value, ...]) lookups, all
    # others are errors.
    def get_prep_lookup(self, lookup_type, value):
        if lookup_type in ('exact', 'in'):
            return super().get_prep_lookup(lookup_type, value)
        else:
            raise TypeError(
                'Lookup type {!r} not supported.'.format(lookup_type))

    # Now we enter the slightly undocumented domain where we tell Django about
    # the category/category_id field.

    # Tell Django that this field should use the '{name}_id' attribute on the
    # model. This means that if you declare `category = CategoryField()` in
    # your model, the model's instances  will store that field on attribute
    # `category_id`.
    def get_attname(self):
        return '{}_id'.format(self.name)

    # Tell Django again (?) about our attribute name (see above), and precise
    # that we also want to use '{name}_id' as the column name in SQL.
    def get_attname_column(self):
        attname = self.get_attname()
        return attname, attname

    # This method will get called by Django when instanciating a new model. We
    # precise that we want our `CategoryDescriptor` field to be present so that
    # we can interact with the `category` field in the model instances through
    # this convenient wrapper.
    def contribute_to_class(self, cls, name, virtual_only=False):
        super().contribute_to_class(cls, name, virtual_only=virtual_only)
        setattr(cls, self.name, CategoryDescriptor(self))
