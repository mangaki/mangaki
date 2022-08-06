# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from rest_framework.documentation import include_docs_urls
from django.urls import re_path

from mangaki.api.cards import get_card
from mangaki.api.tasks import task_status, user_tasks
from mangaki.api.mal import import_from_mal
from mangaki.api.user import (update_user_profile, delete_user_profile,
                              export_user_data, get_user_and_friends_positions)

urlpatterns = [
    re_path(r'^tasks/(?P<task_id>[\w\d\-\.]+)/?$',
        task_status, name='api-get-task-status'),
    re_path(r'^tasks/$',
        user_tasks, name='api-get-user-tasks'),
    re_path(r'^cards/(?P<category>\w+)/(?P<slot_sort_type>\w+)$',
        get_card, name='api-get-card'),
    re_path(r'^mal/import/(?P<mal_username>.+)$',
        import_from_mal, name='api-mal-import'),
    re_path(r'^user/profile$',
        update_user_profile, name='api-update-my-profile'),
    re_path(r'^user/position/(?P<algo_name>\w+)$',
        get_user_and_friends_positions, name='get-user-position'),
    re_path(r'^user/delete$',
        delete_user_profile, name='api-delete-my-account'),
    re_path(r'^user/export$',
        export_user_data, name='api-export-my-data'),
    re_path(r'^doc', include_docs_urls(title='Mangaki API'))
]
