from django import template

from mangaki.utils import ratings

register = template.Library()


@register.filter()
def has_anonymous_ratings(request):
    return ratings.has_anonymous_ratings(request.session)
