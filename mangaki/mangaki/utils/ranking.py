# Some of these values have related indexes in the database. Please don't
# change them without issuing the appropriate migrations.
TOP_MIN_RATINGS = 80
RANDOM_MIN_RATINGS = 28
RANDOM_MAX_DISLIKES = 17
RANDOM_RATIO = 3.0

# This must be coherent with the controversy computation in SQL in
# management/commands/ranking.py
# Don't change one without the other!
def controversy(nb):
    nb_likes, nb_dislikes = nb['like'], nb['dislike']
    if nb_likes == 0 or nb_dislikes == 0:
        return 0
    return (nb_likes + nb_dislikes) ** min(float(nb_likes) / nb_dislikes, float(nb_dislikes) / nb_likes)

