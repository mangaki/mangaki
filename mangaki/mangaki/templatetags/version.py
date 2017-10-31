from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag(takes_context=False)
def mangaki_version():
    return settings.VERSION

@register.simple_tag(takes_context=False)
def mangaki_revision():
    try:
        parts = settings.VERSION.split('+')
        rev, _ = parts[-1].split('.')
        return rev[1:]
    except:
        return '' # just go to latest commit on master.
