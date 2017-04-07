from django import template
from mangaki.utils import ratings
from django.urls import reverse_lazy

register = template.Library()

ANONYMOUS_BANNER_BLACKLIST = (reverse_lazy('my-profile'), reverse_lazy('account_signup'), reverse_lazy('account_login'))


@register.filter()
def has_anonymous_ratings(request):
    return ratings.has_anonymous_ratings(request.session)


@register.filter()
def should_show_anonymous_banner(request):
    path = request.get_full_path()
    cleaned_path = path.split('?')[0]

    return cleaned_path not in ANONYMOUS_BANNER_BLACKLIST
