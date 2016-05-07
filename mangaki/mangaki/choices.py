from collections import OrderedDict

ORIGIN_CHOICES = (
    ("japon", "Japon"),
    ("coree", "Coree"),
    ("france", "France"),
    ("chine", "Chine"),
    ("usa", "USA"),
    ("allemagne", "Allemagne"),
    ("taiwan", "Taiwan"),
    ("espagne", "Espagne"),
    ("angleterre", "Angleterre"),
    ("hong-kong", "Hong Kong"),
    ("italie", "Italie"),
    ("inconnue", "Inconnue"),
    ("intl", "International")
)

TYPE_CHOICES = (
    ("seinen", "Seinen"),
    ("shonen", "Shonen"),
    ("shojo", "Shojo"),
    ("yaoi", "Yaoi"),
    ("sonyun-manhwa", "Sonyun-Manhwa"),
    ("kodomo", "Kodomo"),
    ("ecchi-hentai", "Ecchi-Hentai"),
    ("global-manga", "Global-Manga"),
    ("manhua", "Manhua"),
    ("josei", "Josei"),
    ("sunjung-sunjeong", "Sunjung-Sunjeong"),
    ("chungnyun", "Chungnyun"),
    ("yuri", "Yuri"),
    ("dojinshi-parodie", "Dojinshi-Parodie"),
    ("manhwa", "Manhwa"),
    ("yonkoma", "Yonkoma")
)

TOP_CATEGORY_CHOICES = (
    ("directors", "Réalisateurs"),
    ("authors", "Auteurs"),
    ("composers", "Compositeurs"),
)

CATEGORIES = OrderedDict([
    (1, {'slug': 'anime', 'name': 'Anime'}),
    (2, {'slug': 'manga', 'name': 'Manga'}),
    (3, {'slug': 'album', 'name': 'Album'}),
])
REVERSE_CATEGORY = {v['slug']: k for k, v in CATEGORIES.items()}
CATEGORY_CHOICES = [(k, v['name']) for k, v in CATEGORIES.items()]

class Category:
    __slots__ = ['pk']

    def __init__(self, key):
        """Creates a Category instance based on either a slug or ID.

        Raises KeyError if the argument was not a valid category slug or ID.
        """
        self.pk = REVERSE_CATEGORY.get(key, None)
        if self.pk is None:
            try:
                self.pk = int(key)
            except (TypeError, ValueError):
                pass
        if self.pk not in CATEGORIES:
            raise ValueError(
                '%r: Invalid category identifier' % key)

    @property
    def id(self):
        return self.pk

    def __getattr__(self, attr):
        try:
            return CATEGORIES[self.pk][attr]
        except KeyError:
            raise AttributeError("{!r} object has no attribute {!r}".format(
                type(self).__name__, attr))

    def __int__(self):
        return self.pk

    def __str__(self):
        return CATEGORIES[self.pk]['name']

    def __repr__(self):
        return '<Category #{}: {}>'.format(self.pk, self)
