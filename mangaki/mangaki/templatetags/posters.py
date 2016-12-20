from django import template
from django.contrib.staticfiles.templatetags.staticfiles import static

register = template.Library()

@register.simple_tag(takes_context=True)
def poster_url(context, work):
    if work is None:
        return static('img/chiro.gif')
    return work.safe_poster(context.request.user)
