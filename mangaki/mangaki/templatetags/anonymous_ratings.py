from django import template

from mangaki.utils import ratings

register = template.Library()


@register.filter()
def has_anonymous_ratings(request):
    return request.user.is_anonymous and ratings.has_anonymous_ratings(request.session)
