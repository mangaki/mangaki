from django.utils.translation import ugettext_lazy as _


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
    ("directors", _("Directors")),
    ("authors", _("Authors")),
    ("composers", _("Composers"))
)

CLUSTER_CHOICES = (
    ('unprocessed', 'Non traité'),
    ('accepted', 'Accepté'),
    ('rejected', 'Rejeté')
)

RELATION_TYPE_CHOICES = (
    ('', 'Inconnu'),
    ('prequel', 'Préquelle'),
    ('sequel', 'Suite'),
    ('summary', 'Résumé'),
    ('side_story', 'Histoire parallèle'),
    ('parent_story', 'Histoire mère'),
    ('alternative_setting', 'Univers alternatif'),
    ('same_setting', 'Univers commun'),
    ('other', 'Spécial'),
    ('adaptation', 'Adaptation')
)

SUGGESTION_PROBLEM_CHOICES = (
    ("title", "Le titre n'est pas le bon"),
    ("poster", "Le poster ne convient pas"),
    ("synopsis", "Le synopsis comporte des erreurs"),
    ("author", "L'auteur n'est pas le bon"),
    ("composer", "Le compositeur n'est pas le bon"),
    ("double", "Ceci est un doublon"),
    ("nsfw", "L'oeuvre est NSFW"),
    ("n_nsfw", "L'oeuvre n'est pas NSFW"),
    ("ref", "Proposer une URL (MyAnimeList, AniDB, Icotaku, VGMdb, etc.)")
)
