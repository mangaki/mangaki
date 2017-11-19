# Here goes the Celery tasks.
import json

import redis
from celery.utils.log import get_task_logger
from django.db import IntegrityError

from .celery import app
from django.contrib.auth.models import User
from django.conf import settings

from mangaki.models import UserBackgroundTask
import mangaki.utils.mal as mal

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
