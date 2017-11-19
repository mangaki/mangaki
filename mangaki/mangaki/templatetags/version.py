from django import template
from django.conf import settings

register = template.Library()

def parse_mangaki_version(version: str) -> str:
    """
    Parse Mangaki version from a setuptools-scm like string.

    >>> parse_mangaki_version('v0.5.3')
    'v0.5.3'
    >>> parse_mangaki_version('v0.2.dev32+g42148.0034934')
    'v0.2.dev32'
    """
    return settings.VERSION.split('+')[0]

def parse_mangaki_revision(version: str) -> str:
    """
    Parse Mangaki revision to build a link to the repository.

    >>> parse_mangaki_revision('v0.5.3')
    ''
    >>> parse_mangaki_revision('v10.1.0')
    ''
    >>> parse_mangaki_revision('v10.2.0.dev42+g42400A3.48234')
    '42400A3'
    """

    try:
        parts = version.split('+')
        if len(parts) > 1:
            rev = parts[-1].split('.')[0]
            return rev[1:]
        else:
            return ''
    except:
        return '' # just go to latest commit on master.


@register.simple_tag(takes_context=False)
def mangaki_version():
    return parse_mangaki_version(settings.VERSION)

@register.simple_tag(takes_context=False)
def mangaki_revision():
    return parse_mangaki_revision(settings.VERSION)
