from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    args = ''
    help = 'Update rankings'

    def handle(self, *args, **options):
        cursor = connection.cursor()

        # Since we are using PostgreSQL, using the WITH ... UPDATE constructs
        # gives us much faster updates than the Django ORM. Not that is matters
        # that much for a maintenance operation...
        # The controversy computation must stay identical to the one in
        # utils/ranking.py, don't change one without the other!
        cursor.execute("""
WITH nb AS (SELECT
        work_id,
        COUNT(CASE WHEN choice = 'favorite' THEN 1 END) AS favorites,
        COUNT(CASE WHEN choice = 'like' THEN 1 END) as likes,
        COUNT(CASE WHEN choice = 'dislike' THEN 1 END) as dislikes,
        COUNT(CASE WHEN choice = 'neutral' THEN 1 END) as neutrals,
        COUNT(CASE WHEN choice = 'willsee' THEN 1 END) as willsees,
        COUNT(CASE WHEN choice = 'wontsee' THEN 1 END) as wontsees
    FROM mangaki_rating GROUP BY work_id)
UPDATE mangaki_work
SET
    nb_likes = nb.likes,
    nb_dislikes = nb.dislikes,
    sum_ratings = 5.*nb.favorites+2.5*nb.likes-2.*nb.dislikes-0.1*nb.neutrals+0.5*nb.willsees-0.5*nb.wontsees,
    nb_ratings = nb.favorites + nb.likes + nb.dislikes + nb.neutrals,
    controversy = CASE
        WHEN nb_likes = 0 OR nb_dislikes = 0 THEN 0
        ELSE (nb_likes + nb_dislikes)::float ^ LEAST(nb_likes::float / nb_dislikes::float, nb_dislikes::float / nb_likes::float)
    END
FROM nb WHERE nb.work_id = mangaki_work.id;
""")
