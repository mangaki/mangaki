from django.conf.urls import include, url
from mangaki.router import router
from rest_framework_jwt.views import obtain_jwt_token

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'api/', include('rest_framework.urls')),
    url(r'auth/', obtain_jwt_token)
]
