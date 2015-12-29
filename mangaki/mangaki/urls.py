from django.conf.urls import include, url
from mangaki.router import router

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'api/', include('rest_framework.urls'))
]
