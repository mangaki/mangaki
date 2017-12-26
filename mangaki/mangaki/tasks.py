# Here goes the Celery tasks.
import json

import redis
from celery.utils.log import get_task_logger
from django.db import IntegrityError
from django.db.models import Count, Q

from mangaki.utils.work_merge import create_work_cluster, merge_work_clusters
from .celery import app
from django.contrib.auth.models import User
from django.conf import settings

from mangaki.models import UserBackgroundTask, Work, WorkCluster
import mangaki.utils.mal as mal
import redis_lock

MAL_IMPORT_TAG = 'MAL_IMPORT'

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


def get_current_mal_import(user: User):
    return user.background_tasks.filter(tag=MAL_IMPORT_TAG).first()

# 10 minutes.

DEFAULT_LOCK_EXPIRATION_TIME = 10*60


@app.task(name='look_for_workclusters', ignore_result=True)
def look_for_workclusters(steal_workcluster: bool = False):
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
        logger.info('Compresssing redundant work clusters.')
        for work in Work.objects.prefetch_related('workcluster_set').iterator():
            # Only merge automatic unprocessed work clusters.
            cluster_filter = Q(status='unprocessed')
            if not steal_workcluster:
                cluster_filter |= Q(user=None)
            clusters = work.workcluster_set.filter(cluster_filter).order_by('id').all()
            if len(clusters) > 1:
                merge_work_clusters(*clusters)
                logger.info('{} clusters merged.'.format(len(clusters)))
        logger.info('Compression done.')


@app.task(name='import_mal', bind=True, ignore_result=True)
def import_mal(self, mal_username: str, mangaki_username: str):
    r = redis.StrictRedis(connection_pool=redis_pool)

    def update_details(count, current_index, current_title):
        payload = {
            'count': count,
            'currentWork': {
                'index': current_index,
                'title': current_title
            }
        }

        r.set('tasks:{task_id}:details'.format(task_id=self.request.id),
              json.dumps(payload))

    user = User.objects.get(username=mangaki_username)
    if user.background_tasks.filter(tag=MAL_IMPORT_TAG).exists():
        logger.debug('[{}] MAL import already in progress. Ignoring.'.format(user))
        return

    bg_task = UserBackgroundTask(owner=user, task_id=self.request.id, tag=MAL_IMPORT_TAG)
    bg_task.save()
    logger.info('[{}] MAL import task created: {}.'.format(user, bg_task.task_id))
    try:
        mal.import_mal(mal_username, mangaki_username, update_callback=update_details)
    except IntegrityError:
        logger.exception('MAL import failed due to integrity error')
    finally:
        bg_task.delete()
        r.delete('tasks:{}:details'.format(self.request.id))
        logger.info('[{}] MAL import task recycled and deleted.'.format(user))
