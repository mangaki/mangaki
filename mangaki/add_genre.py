from mangaki.models import Genre

GENRE_CHOICES = (
    ("fantastique", "Fantastique"),
    ("romance", "Romance"),
    ("aventure", "Aventure"),
    ("tranche-de-vie", "Tranche-de-vie"),
    ("comedie", "Comedie"),
    ("suspense", "Suspense"),
    ("action", "Action"),
    ("gay-lesbien", "Gay-Lesbien"),
    ("historique", "Historique"),
    ("erotique", "Erotique"),
    ("drame", "Drame"),
    ("science-fiction", "Science-fiction"),
    ("social", "Social"),
    ("humour", "Humour"),
    ("sport", "Sport"),
    ("histoires-courtes", "Histoires-courtes"),
    ("conte", "Conte"),
    ("horreur", "Horreur"),
    ("policier", "Policier"),
    ("enfants", "Enfants"),
    ("heroic-fantasy", "Heroic-fantasy"),
    ("samourai", "Samourai"),
    ("musique", "Musique"),
    ("gastronomie", "Gastronomie"),
    ("thriller", "Thriller"),
    ("parodie", "Parodie"),
    ("philosophique", "Philosophique"),
    ("documentaire", "Documentaire"),
    ("medical", "Medical"),
    ("emotion", "Emotion"),
    ("animaux", "Animaux"),
    ("loisir", "Loisir")
)


def run():
    for _, genre in GENRE_CHOICES:
        Genre(title=genre).save()
    print('OK')
