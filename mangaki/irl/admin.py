# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from django.contrib import admin
from irl.models import Partner


class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'image']

admin.site.register(Partner, PartnerAdmin)
