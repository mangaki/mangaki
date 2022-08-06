# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from rest_framework.documentation import include_docs_urls
from django.conf.urls import url

from mangaki.api.cards import get_card
from mangaki.api.tasks import task_status, user_tasks
from mangaki.api.mal import import_from_mal
from mangaki.api.user import (update_user_profile, delete_user_profile,
                              export_user_data, get_user_and_friends_positions)

urlpatterns = [
    url(r'^tasks/(?P<task_id>[\w\d\-\.]+)/?$',
        task_status, name='api-get-task-status'),
    url(r'^tasks/$',
        user_tasks, name='api-get-user-tasks'),
    url(r'^cards/(?P<category>\w+)/(?P<slot_sort_type>\w+)$',
        get_card, name='api-get-card'),
    url(r'^mal/import/(?P<mal_username>.+)$',
        import_from_mal, name='api-mal-import'),
    url(r'^user/profile$',
        update_user_profile, name='api-update-my-profile'),
    url(r'^user/position/(?P<algo_name>\w+)$',
        get_user_and_friends_positions, name='get-user-position'),
    url(r'^user/delete$',
        delete_user_profile, name='api-delete-my-account'),
    url(r'^user/export$',
        export_user_data, name='api-export-my-data'),
    url(r'^doc', include_docs_urls(title='Mangaki API'))
]
