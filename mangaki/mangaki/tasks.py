# Here goes the Celery tasks.
import json

import redis
from celery.utils.log import get_task_logger

from .celery import app
from django.contrib.auth.models import User
from django.conf import settings

from mangaki.models import UserBackgroundTask
import mangaki.utils.mal as mal

MAL_IMPORT_TAG = 'MAL_IMPORT'

logger = get_task_logger(__name__)
redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL)


def get_current_mal_import(user: User):
    return user.background_tasks.filter(tag=MAL_IMPORT_TAG).first()


@app.task(name='import_mal', bind=True)
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
    logger.debug('[{}] MAL import task created: {}.'.format(user, bg_task.task_id))
    mal.import_mal(mal_username, mangaki_username)
    bg_task.delete()
    logger.debug('[{}] MAL import task recycled and deleted.'.format(user))
