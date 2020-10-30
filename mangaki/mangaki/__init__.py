from mangaki.celery import app as celery_app

default_app_config = 'mangaki.apps.MangakiConfig'

__all__ = ["celery_app", ]
