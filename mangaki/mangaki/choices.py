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

WORK_CATEGORY_CHOICES = (
    (0, "Anime"),
    (1, "Manga"),
    (2, "Album"),
)

WORK_CATEGORY_OF_ID = ['anime', 'manga', 'album']
ID_OF_WORK_CATEGORY = {
    v: i for i, v in enumerate(WORK_CATEGORY_OF_ID)
}
