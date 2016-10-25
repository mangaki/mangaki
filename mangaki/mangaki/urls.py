from django.contrib.auth.decorators import login_required
from django.conf.urls.static import static
from django.conf.urls import handler400, handler404, handler500
from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django_js_reverse.views import urls_js
from discourse import views as discourse_views
from mangaki import views
from mangaki.settings import DEBUG

urlpatterns = [
    # Examples:
    # url(r'^$', views.home, name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^jsreverse/$', urls_js, name='js_reverse'),

    url(r'^$', views.index, name='home'),
    url(r'^data/(?P<category>\w+)\.json$', views.get_works, name='get-work'),
    url(r'^data/reco/(?P<category>\w+)/(?P<editor>\w+)\.json$', views.get_reco_list, name='get-reco-list'),
    url(r'^data/card/(?P<category>\w+)/(?P<sort_id>\d+)\.json$', views.CardList.as_view(), name='get-card'),
    url(r'^getuser/(?P<work_id>\w+)\.json$', views.get_user_for_recommendations, name='get-user-for-reco'),
    url(r'^getuser\.json$', views.get_users, name='get-user'),
    url(r'^recommend/(?P<work_id>\w+)/(?P<target_id>\w+)$', views.recommend_work, name='reco-work'),
    url(r'^removeReco/(?P<work_id>\d+)/(?P<username>\w+)/(?P<targetname>\w+)$', views.remove_reco, name='remove-reco'),
    url(r'^removeReco/(?P<targetname>\w+)$', views.remove_all_reco, name='remove-all-reco'),
    url(r'^users/', views.UserList.as_view()),
    url(r'^user/', include('allauth.urls')),
    url(r'^u/(?P<username>.+)$', views.get_profile, name='profile'),  # login_required?
    url(r'^reco/$', views.get_reco, name='reco'),
    url(r'^artist/(?P<pk>\d+)$', views.ArtistDetail.as_view(), name='artist-detail'),
    url(r'^artist/(?P<artist_id>\d+)/add/(?P<work_id>\d+)$', views.add_pairing, name='add-pairing'),
    url(r'^vote/(?P<work_id>\d+)$', views.rate_work, name='vote'),
    url(r'^shared/$', views.update_shared, name='shared'),
    url(r'^nsfw/$', views.update_nsfw, name='nsfw'),
    url(r'^newsletter/$', views.update_newsletter, name='newsletter'),
    url(r'^reco_willsee/$', views.update_reco_willsee, name='reco-willsee'),
    url(r'^mal/(?P<mal_username>.+)$', views.import_from_mal, name='import-mal'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^discourse/sso$', discourse_views.sso),
    url(r'^about/$', views.about, name='about'),
    url(r'^faq/$', views.faq_index, name='faq'),
    url(r'^cgu/$', views.MarkdownView.as_view(), kwargs={'slug': 'cgu'}, name='cgu'),
    url(r'^events/$', views.events, name='events'),
    # url(r'^lookup/$', views.lookup_work'),
    url(r'^top/(?P<category_slug>[\w-]+)/$', views.top, name='top'),
    url(r'^event/(?P<pk>\d+)$', views.EventDetail.as_view(), name='event-detail'),
    url(r'^(?P<category>[\w-]+)/$', views.WorkList.as_view(), name='work-list'),
    url(r'^(?P<category>[\w-]+)/(?P<pk>\d+)$', views.WorkDetail.as_view(), name='work-detail'),
]

handler404 = views.page_not_found
handler403 = views.permission_denied

if DEBUG:  # https://docs.djangoproject.com/en/1.10/howto/static-files/#serving-files-uploaded-by-a-user-during-development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
