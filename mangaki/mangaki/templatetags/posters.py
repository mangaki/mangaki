from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def poster_url(context, work):
    return work.safe_poster(context.request.user)
