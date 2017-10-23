from rest_framework.documentation import include_docs_urls
from django.conf.urls import url

from mangaki.api.cards import get_card
from mangaki.api.tasks import task_status, user_tasks

urlpatterns = [
    url(r'^tasks/(?P<task_id>[\w\d\-\.]+)/?$',
        task_status, name='api-get-task-status'),
    url(r'^tasks/$',
        user_tasks, name='api-get-user-tasks'),
    url(r'^cards/(?P<category>\w+)/(?P<slot_sort_type>\w+)$',
        get_card, name='api-get-card'),
    url(r'^doc', include_docs_urls(title='Mangaki API'))
]
