from rest_framework.documentation import include_docs_urls
from django.conf.urls import url

from mangaki.api.cards import get_card

urlpatterns = [
    url(r'^cards/(?P<category>\w+)/(?P<slot_sort_type>\w+)$',
        get_card, name='api-get-card'),
    url(r'^doc', include_docs_urls(title='Mangaki API'))
]
