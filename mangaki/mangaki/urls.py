from django.contrib.auth.decorators import login_required
from django.conf.urls import patterns, include, url
from django.contrib import admin
from mangaki.views import AnimeDetail, AnimeList, MangaDetail, MangaList, MarkdownView, UserList
from discourse import views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'mangaki.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', 'mangaki.views.index'),
    url(r'^data/(?P<category>\w+)\.json$', 'mangaki.views.get_works'),
    url(r'^data/anime/(?P<query>.+)\.json$', 'mangaki.views.get_extra_anime'),
    url(r'^data/manga/(?P<query>.+)\.json$', 'mangaki.views.get_extra_manga'),
    url(r'^data/reco/(?P<category>\w+)/(?P<editor>\w+)\.json$', 'mangaki.views.get_reco_list'),
    url(r'^data/card/(?P<category>\w+)/(?P<sort_id>\d+)\.json$', 'mangaki.views.get_card'),
    url(r'^recommend/(?P<work_id>\w+)/(?P<target_id>\w+)/(?P<query>.+)\.json$', 'mangaki.views.get_user_for_recommendations'),
    url(r'^users/', UserList.as_view()),
    url(r'^user/', include('allauth.urls')),
    url(r'^u/(?P<username>.+)$', 'mangaki.views.get_profile'), # login_required?
    url(r'^reco/$', 'mangaki.views.get_reco'),
    url(r'^anime/$', AnimeList.as_view()),
    url(r'^anime/(?P<pk>\d+)$', AnimeDetail.as_view()),
    url(r'^anime/(?P<pk>\d+)/nsfw$', 'mangaki.views.report_nsfw'),
    url(r'^manga/$', MangaList.as_view()),
    url(r'^manga/(?P<pk>\d+)$', MangaDetail.as_view()),
    url(r'^anime/(?P<pk>\d+)/nsfw$', 'mangaki.views.report_nsfw'),
    url(r'^work/(?P<work_id>\d+)$', 'mangaki.views.rate_work'),
    url(r'^shared/$', 'mangaki.views.update_shared'),
    url(r'^nsfw/$', 'mangaki.views.update_nsfw'),
    url(r'^reco_willsee/$', 'mangaki.views.update_reco_willsee'),
    url(r'^mal/(?P<mal_username>.+)$', 'mangaki.views.import_from_mal'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^discourse/sso$', views.sso),
    url(r'^about/$', 'mangaki.views.about'),
    url(r'^events/$', 'mangaki.views.events'),
    # url(r'^lookup/$', 'mangaki.views.lookup_work'),
    url(r'^(?P<slug>[\w-]+)/$', MarkdownView.as_view()),
)
