from django.utils.translation import ugettext_lazy as _


ORIGIN_CHOICES = (
    ("japon", _("Japan")),
    ("coree", _("Korea")),
    ("france", _("France")),
    ("chine", _("China")),
    ("usa", _("US")),
    ("allemagne", _("Germany")),
    ("taiwan", _("Taiwan")),
    ("espagne", _("Spain")),
    ("angleterre", _("UK")),
    ("hong-kong", _("Hong Kong")),
    ("italie", _("Italia")),
    ("inconnue", _("Unknown")),
    ("intl", _("International"))
)

TYPE_CHOICES = (
    ("seinen", _("Seinen")),
    ("shonen", _("Shonen")),
    ("shojo", _("Shojo")),
    ("yaoi", _("Yaoi")),
    ("sonyun-manhwa", _("Sonyun-Manhwa")),
    ("kodomo", _("Kodomo")),
    ("ecchi-hentai", _("Ecchi-Hentai")),
    ("global-manga", _("Global-Manga")),
    ("manhua", _("Manhua")),
    ("josei", _("Josei")),
    ("sunjung-sunjeong", _("Sunjung-Sunjeong")),
    ("chungnyun", _("Chungnyun")),
    ("yuri", _("Yuri")),
    ("dojinshi-parodie", _("Dojinshi-Parody")),
    ("manhwa", _("Manhwa")),
    ("yonkoma", _("Yonkoma"))
)

TOP_CATEGORY_CHOICES = (
    ("directors", _("Directors")),
    ("authors", _("Authors")),
    ("composers", _("Composers"))
)

CLUSTER_CHOICES = (
    ('unprocessed', _("Unprocessed")),
    ('accepted', _("Accepted")),
    ('rejected', _("Rejected"))
)

RELATION_TYPE_CHOICES = (
    ('', _("Unknown")),
    ('prequel', _("Prequel")),
    ('sequel', _("Sequel")),
    ('summary', _("Summary")),
    ('side_story', _("Side story")),
    ('parent_story', _("Parent story")),
    ('alternative_setting', _("Alternative setting")),
    ('same_setting', _("Same setting")),
    ('other', _("Special")),
    ('adaptation', _("Adaptation"))
)

SUGGESTION_PROBLEM_CHOICES = (
    ("title", _("Wrong title")),
    ("poster", _("Wrong poster")),
    ("synopsis", _("Synopsis contains mistakes")),
    ("author", _("Wrong author")),
    ("composer", _("Wrong composer")),
    ("double", _("This is a duplicate")),
    ("nsfw", _("Work is Not Safe for Work")),
    ("n_nsfw", _("Work is actually Safe for Work")),
    ("ref", _("Suggest a reference URL (MyAnimeList, AniDB, Icotaku, VGMdb, etc.)"))
)

STAFF_TYPICAL_CHOICES = (
    _('Director'),
    _('Composer'),
    _('Author'),
    _('Mangaka'),
    _('Screenwriter')
)

SORT_MODE_CHOICES = (
    ('mosaic', _('Mosaic')),
    ('new', _('Recent')),
    ('top', _('Top')),
    ('popularity', _('Popular')),
    ('pearls', _('Pearls')),
    ('controversy', _('Controversial')),
    ('random', _('Random')),
    ('alpha', _('A-Z'))
)
