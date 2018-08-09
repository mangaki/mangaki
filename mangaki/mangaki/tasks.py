# Here goes the Celery tasks.
import functools
import json

import redis
from celery.app.task import Task
from celery.utils.log import get_task_logger
from django.db import IntegrityError
from django.db.models import Count, Q

from mangaki.utils.work_merge import create_work_cluster, merge_work_clusters
from mangaki.utils.singleton import Singleton
from mangaki.wrappers import anilist
from .celery import app
from django.contrib.auth.models import User
from django.conf import settings

from mangaki.models import UserBackgroundTask, Work, WorkCluster
import mangaki.utils.mal as mal
import redis_lock

logger = get_task_logger(__name__)
if settings.REDIS_URL:
    redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL)
    try:
        redis.StrictRedis(connection_pool=redis_pool).ping()
    except (redis.exceptions.ConnectionError,
            redis.exceptions.ResponseError):
        redis_pool.disconnect()
        redis_pool = None
else:
    redis_pool = None

# 10 minutes.
DEFAULT_LOCK_EXPIRATION_TIME = 10*60


@app.task(name='look_for_workclusters', ignore_result=True)
def look_for_workclusters(steal_workcluster: bool = False):
    """
    A maintenance Celery Task which clusters works in the database,
    creating WorkCluster objects.

    Args:
        steal_workcluster (bool): Allow for this task to merge non-automatic WorkClusters with automatic ones.
            (i.e. if a WorkCluster is deemed to be the same but its user is human,
            we would steal or not its WorkCluster to merge it with a new one).

    Returns: None.

    """

    logger.info('Looking for easy WorkCluster to create...')
    with redis_lock.Lock(redis.StrictRedis(connection_pool=redis_pool),
                         'lock-wc-lookout',
                         expire=DEFAULT_LOCK_EXPIRATION_TIME):
        logger.info('Acquired Redis lock.')
        # MAL-created duplicates
        duplicates = Work.objects.values('title', 'category_id').annotate(Count('id')).filter(id__count__gte=2)
        for dupe in duplicates.iterator():
            works = Work.objects.filter(title=dupe['title']).prefetch_related('workcluster_set')
            cluster = create_work_cluster(works)
            logger.info('Clustered {} works. ({})'.format(len(works), cluster.id))

        logger.info('Clustering done.')
        logger.info('Compressing redundant work clusters.')
        for work in Work.objects.prefetch_related('workcluster_set').iterator():
            # Only merge automatic unprocessed work clusters.
            cluster_filter = Q(status='unprocessed')
            if not steal_workcluster:  # Don't be evil. Don't steal human WorkClusters.
                cluster_filter |= Q(user=None)
            clusters = work.workcluster_set.filter(cluster_filter).order_by('id').all()
            if len(clusters) > 1:
                merge_work_clusters(*clusters)
                logger.info('{} clusters merged.'.format(len(clusters)))
        logger.info('Compression done.')

class BaseImporter:
    name = None

    @property
    def tag(self):
        return '{}_IMPORT_TAG'.format(self.name.upper())

    @property
    def task_suffix(self):
        return self.name.lower()

    @staticmethod
    def _update_details_cb(r, request, payload):
        r.set('tasks:{task_id}:details'.format(
            task_id=request.id
        ), json.dumps(payload))

    def get_current_import_for(self, user: User):
        if self.name is None:
            raise NotImplementedError

        return user.background_tasks.filter(tag=self.tag).first()

    def run(self, mangaki_username: str, update_callback, *args):
        raise NotImplementedError

    def start(self, task: Task, mangaki_username: str, user_arguments):
        r = redis.StrictRedis(connection_pool=redis_pool)

        user = User.objects.get(username=mangaki_username)
        if user.background_tasks.filter(tag=self.tag).exists():
            logger.debug('[{}] {} import already in progress. Ignoring.'.format(user,
                                                                                self.name))
            return

        bg_task = UserBackgroundTask(owner=user, task_id=task.request.id, tag=self.tag)
        bg_task.save()
        logger.info('[{}] {} import task created: {}.'.format(user,
                                                              self.name, bg_task.task_id))
        try:
            update_cb = functools.partial(self._update_details_cb, r, task.request)
            self.run(mangaki_username, update_cb, *user_arguments)
        except IntegrityError:
            logger.exception('{} import failed due to integrity error'.format(self.name))
        finally:
            bg_task.delete()
            r.delete('tasks:{}:details'.format(task.request.id))
            logger.info('[{}] {} import task recycled and deleted.'.format(user, self.name))


class MALImporter(BaseImporter, metaclass=Singleton):
    name = 'MAL'

    def run(self, mangaki_username: str, update_cb, *args):
        mal_username, = args

        mal.import_mal(mal_username, mangaki_username, update_callback=update_cb)


class AniListImporter(BaseImporter, metaclass=Singleton):
    name = 'AniList'

    def run(self, mangaki_username: str, update_cb, *args):
        anilist_username, = args

        anilist.import_anilist(anilist_username, mangaki_username, update_callback=update_cb,
                               build_related=settings.ANILIST_IMPORT.get('BUILD_RELATED_WORKS'))


def build_import_task(importer_class):
    @app.task(name='import_{}'.format(importer_class.task_suffix), bind=True, ignore_result=True)
    def perform_import(self, mangaki_username: str, *user_args):
        klass = importer_class()
        klass.start(self, mangaki_username, *user_args)

    return perform_import


import_anilist = build_import_task(AniListImporter)
import_mal = build_import_task(MALImporter)
