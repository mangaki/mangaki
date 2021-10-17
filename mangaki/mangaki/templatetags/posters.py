# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from django import template
from django.contrib.staticfiles.templatetags.staticfiles import static

register = template.Library()

@register.simple_tag(takes_context=True)
def poster_url(context, work, bypass_nsfw_settings=None):
    if work is None:
        return static('img/chiro.gif')
    if bypass_nsfw_settings:
        return work.poster_url
    return work.safe_poster(context.request.user)
