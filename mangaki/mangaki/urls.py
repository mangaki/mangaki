from django.contrib.auth.decorators import login_required
from django.conf.urls import include, url
from django.contrib import admin
from discourse import views as discourse_views
from mangaki import views
from mangaki import api

urlpatterns = [
    # Examples:
    # url(r'^$', views.home, name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^api/', include(api.router.urls, namespace='api')),
    url(r'^$', views.index),
    url(r'^data/(?P<category>\w+)\.json$', views.get_works),
    url(r'^data/reco/(?P<category>\w+)/(?P<editor>\w+)\.json$', views.get_reco_list),
    url(r'^data/card/(?P<category>\w+)/(?P<sort_id>\d+)\.json$', views.get_card),
    url(r'^getuser/(?P<work_id>\w+)\.json$', views.get_user_for_recommendations),
    url(r'^getuser\.json$', views.get_users),
    url(r'^recommend/(?P<work_id>\w+)/(?P<target_id>\w+)$', views.recommend_work),
    url(r'^removeReco/(?P<work_id>\d+)/(?P<username>\w+)/(?P<targetname>\w+)$', views.remove_reco),
    url(r'^removeReco/(?P<targetname>\w+)$', views.remove_all_reco),
    url(r'^users/', views.UserList.as_view()),
    url(r'^user/', include('allauth.urls')),
    url(r'^u/(?P<username>.+)$', views.get_profile),  # login_required?
    url(r'^reco/$', views.get_reco),
    url(r'^anime/$', views.WorkList.as_view(), {'category': 'anime' }, name='anime-list'),
    url(r'^anime/(?P<pk>\d+)$', views.WorkDetail.as_view(), {'category': 'anime'}, name='anime-detail'),
    url(r'^anime/(?P<pk>\d+)/nsfw$', views.report_nsfw),
    url(r'^album/(?P<pk>\d+)$', views.WorkDetail.as_view(), {'category': 'album'}, name='album-detail'),
    url(r'^album/(?P<pk>\d+)/nsfw$', views.report_nsfw),
    url(r'^manga/$', views.WorkList.as_view(), {'category': 'manga' }, name='manga-list'),
    url(r'^manga/(?P<pk>\d+)$', views.WorkDetail.as_view(), {'category': 'manga'}, name='manga-detail'),
    url(r'^manga/(?P<pk>\d+)/nsfw$', views.report_nsfw),
    url(r'^work/(?P<pk>\d+)$', views.WorkDetail.as_view(), name='work-detail'),
    url(r'^work/(?P<pk>\d+)/nsfw$', views.report_nsfw),
    url(r'^artist/(?P<pk>\d+)$', views.ArtistDetail.as_view(), name='artist-detail'),
    url(r'^artist/(?P<artist_id>\d+)/add/(?P<work_id>\d+)$', views.add_pairing),
    url(r'^vote/(?P<work_id>\d+)$', views.rate_work),
    url(r'^shared/$', views.update_shared),
    url(r'^nsfw/$', views.update_nsfw),
    url(r'^newsletter/$', views.update_newsletter),
    url(r'^reco_willsee/$', views.update_reco_willsee),
    url(r'^mal/(?P<mal_username>.+)$', views.import_from_mal),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^discourse/sso$', discourse_views.sso),
    url(r'^about/$', views.about),
    url(r'^events/$', views.events),
    url(r'^unsubscribe/(?P<pk>\d+)/(?P<key>\w+)$', views.unsubscribe),
    # url(r'^lookup/$', views.lookup_work'),
    url(r'^(?P<slug>[\w-]+)/$', views.MarkdownView.as_view()),
    url(r'^top/(?P<category_slug>[\w-]+)/$', views.top),
    url(r'^event/(?P<pk>\d+)$', views.EventDetail.as_view(), name='event-detail'),
]
