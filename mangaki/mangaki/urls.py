from django.contrib.auth.decorators import login_required
from django.conf.urls import patterns, include, url
from django.contrib import admin
from mangaki.views import AnimeDetail, AnimeList, RatingList, MarkdownView

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'mangaki.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', 'mangaki.views.index'),
    url(r'^data/(?P<category>\w+)\.json$', 'mangaki.views.get_works'),
    url(r'^user/', include('allauth.urls')),
    url(r'^list/$', login_required(RatingList.as_view())),
    url(r'^reco/$', 'mangaki.views.get_reco'),
    url(r'^anime/$', AnimeList.as_view()),
    url(r'^anime/(?P<pk>\d+)$', AnimeDetail.as_view()),
    url(r'^work/(?P<work_id>\d+)$', 'mangaki.views.rate_work'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^(?P<slug>[\w-]+)/$', MarkdownView.as_view()),
)
