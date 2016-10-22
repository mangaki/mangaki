from django.core.management.base import BaseCommand
from django.core.management import call_command
from mangaki.models import *
from irl.models import *
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from collections import Counter
from django.db import connection, connections
from django.utils import timezone

import random

MANGAKI_DB_NAME = connections.databases['default']['NAME']
MANGAKI_SEED_DB_NAME = '{}_seed'.format(MANGAKI_DB_NAME)

PARAMETERS = {
    'small': {
        'max_anime': 20,
        'max_manga': 20,
        'max_users': 200
    },
    'big': {
        'max_anime': 200,
        'max_manga': 200,
        'max_users': 500
    }
}

class Command(BaseCommand):
    args = ''
    help = 'Generate (small or big) seed data'

    def add_arguments(self, parser):
        parser.add_argument('size', type=str, help='small or big')
        parser.add_argument('--filename', type=str, default='fixture.json',
                            help='Target path where the fixture will be written')

    def handle(self, *args, **options):
        size, filename = options.get('size'), options.get('filename')
        print('Generating a {} seed data to {}'.format(size.lower(), filename))

        # Save current state of the DB
        self.save_db()
        try:
            self.clean_out_db()
            print('Seed database purged from useless data.')
            # Proceed to the seed data
            chosen_parameters = PARAMETERS[size.lower()]
            ## Limit the works
            self.delete_works(**chosen_parameters)
            ## Anonymize the users
            self.delete_users(**chosen_parameters)
            print('Works and users were limited as per to the {} size seed parameters.'.format(size.lower()))
            ## Save the seed
            self.dump_data(filename)
            print('Seed saved in {}'.format(filename))
        except Exception as e:
            print('Exception occurred during the seed process: {}'.format(e))
        finally:
            # Restore the DB
            self.drop_seed_db()
            print('Temporary database deleted.')

    def create_seed_db(self):
        try:
            conn = connection._nodb_connection
            with conn.cursor() as c:
                c.execute('CREATE DATABASE {} WITH TEMPLATE {}'.format(MANGAKI_SEED_DB_NAME, MANGAKI_DB_NAME))
            conn.close()
            return True
        except Exception as e:
            return False


    def save_db(self):
        if not self.create_seed_db():
            print('Database seems to be already created.')
            self.drop_seed_db()
            created = False
            for x in range(3):
                if self.create_seed_db():
                    created = True
                    break
            if not created:
                print('It seems really impossible to create the seed database, '
                      'investigate what is happening on your computer.')
        try:
            print('Temporary database {} created.'.format(MANGAKI_SEED_DB_NAME))

            if 'seed' in connections.databases:
                print('Warning: `seed` database detected, the parameters will be replaced.')

            connections._databases['seed'] = connections.databases['default'].copy()
            # This is really important to use `NAME` and not `name` !
            connections._databases['seed']['NAME'] = MANGAKI_SEED_DB_NAME

            print('Seed database injected in connections table.')
        except Exception as e:
            print('Exception occurred during database cloning: {} (rolling-back the clone)'.format(e))
            self.drop_seed_db()
            raise e

    def drop_seed_db(self):
        if 'seed' in connections:
            connections['seed'].close()
        conn = connection._nodb_connection
        with conn.cursor() as c:
            c.execute('DROP DATABASE {}'.format(MANGAKI_SEED_DB_NAME))

    def clean_out_db(self):
        """
        Clean out the database of useless and personal data.
        """
        models = [SearchIssue, Suggestion, Recommendation, Pairing,
                  Session, ContentType]

        for model in models:
            model.objects.using('seed').all().delete()


    def delete_works(self, max_anime, max_manga, max_users):
        nb = Counter(Rating.objects.values_list('work_id', flat=True))
        # Distinction between Anime and Manga will disappear with PR #153
        if max_anime:
            work_ids = list(Work.objects\
                            .filter(category__slug='anime')\
                            .values_list('id', flat=True))
            work_ids.sort(key=lambda work_id: -nb[work_id])
            Work.objects.using('seed')\
                .exclude(id__in=work_ids[:max_anime]).delete()
            print('Animes limited.')
        if max_manga:
            work_ids = list(Work.objects\
                            .filter(category__slug='manga')\
                            .values_list('id', flat=True))
            work_ids.sort(key=lambda work_id: -nb[work_id])
            Work.objects.using('seed')\
                .exclude(id__in=work_ids[:max_manga]).delete()
            print('Manga limited.')

        if max_anime or max_manga:
            bundle = []
            for artist_ids in Work.objects.values_list('artists'):
                bundle.extend(artist_ids)
            kept_artist_ids = list(set([x for x in bundle if x is not None]))
            Artist.objects.using('seed')\
                .exclude(id__in=kept_artist_ids).delete()

            print('Artists limited.')

    def delete_users(self, max_anime, max_manga, max_users):
        max_user_id = max(User.objects.values_list('id', flat=True))
        chosen = User.objects.order_by('?')[:max_users]
        kept_ids = chosen.values_list('id', flat=True)
        User.objects.using('seed')\
            .exclude(id__in=kept_ids).delete()
        print('Users limited.')
        self.anonymize_users(max_user_id, max_users)

    def anonymize_users(self, max_user_id, max_users):
        new_ids = random.sample(range(max_user_id + 1, max_user_id + max_users + 1), max_users)
        for user, new_id in zip(User.objects.using('seed').all(), new_ids):
            old_id = user.id
            user.pk = new_id
            user.username = str(new_id)
            user.is_superuser = False
            user.set_password('mangaki')
            user.email = '%d@mangaki.fr' % new_id
            user.date_joined = timezone.now()
            user.last_login = timezone.now()
            user.save(using='seed')
            old_user = User.objects.using('seed').get(id=old_id)
            old_user.rating_set.update(user=user)
            old_user.delete()
        print('Users anonymized.')

    def dump_data(self, path):
        call_command('dumpdata', database='seed', output=path, format='json')
