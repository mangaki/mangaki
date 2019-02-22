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
    return version.split('+')[0]


@register.simple_tag(takes_context=False)
def mangaki_version():
    return parse_mangaki_version(settings.VERSION)
