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
    ('other', 'Spécial')
)
