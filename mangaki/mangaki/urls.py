from django.conf.urls import patterns, include, url
from django.contrib import admin
from mangaki.views import AnimeDetailView

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'mangaki.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', 'mangaki.views.index'),
    url(r'^user/', include('allauth.urls')),
    url(r'^anime/(?P<pk>\d+)$', AnimeDetailView.as_view()),
    url(r'^admin/', include(admin.site.urls)),
)
