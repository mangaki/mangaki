# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import include, re_path
from django.conf.urls.static import static
from django.urls import path
from django.contrib import admin
from django_js_reverse.views import urls_js

from mangaki import views
from mangaki.api.urls import urlpatterns as apipatterns
from mangaki.settings import DEBUG


urlpatterns = [
    # Examples:
    # re_path(r'^$', views.home, name='home'),
    # re_path(r'^blog/', include('blog.urls')),

    re_path('i18n/', include('django.conf.urls.i18n')),

    re_path(r'^jsreverse/$', urls_js, name='js_reverse'),
    re_path(r'^api/', include(apipatterns)),
    re_path(r'^$', views.index, name='home'),
    re_path(r'^data/(?P<category>\w+)\.json$', views.get_works, name='get-work'),
    re_path(r'^data/reco/(?P<algo_name>\w+)/(?P<merge_type>\w+)/(?P<category>\w+)\.json$', views.get_reco_algo_list, name='get-reco-algo-list'),
    re_path(r'^data/reco/(?P<algo_name>\w+)/(?P<category>\w+)\.json$', views.get_reco_algo_list, name='get-reco-algo-list'),
    re_path(r'^getuser/(?P<work_id>\w+)\.json$', views.get_user_for_recommendations, name='get-user-for-reco'),
    re_path(r'^getuser\.json$', views.get_users, name='get-user'),
    re_path(r'^getfriends\.json$', views.get_friends, name='get-friends'),
    re_path(r'^recommend/(?P<work_id>\w+)/(?P<target_id>\w+)$', views.recommend_work, name='reco-work'),
    re_path(r'^removeReco/(?P<work_id>\d+)/(?P<username>\w+)/(?P<targetname>\w+)$', views.remove_reco, name='remove-reco'),
    re_path(r'^removeReco/(?P<targetname>\w+)$', views.remove_all_reco, name='remove-all-reco'),
    re_path(r'^remove_anon_ratings/$', views.remove_all_anon_ratings, name='remove-all-anon-ratings'),
    # We explicitely want to override allauth's signup and login views
    re_path(r'^user/signup/$', views.signup, name="account_signup"),
    re_path(r'^user/login/$', views.login, name="account_login"),
    re_path(r'^user/', include('allauth.urls')),

    re_path(r'^user/deleted/$', views.deleted_account, name='deleted-account'),

    re_path(r'^profile/$', views.get_profile_works, name='my-profile'),
    re_path(r'^profile/(?P<category>\w+)/$', views.get_profile_works, name='my-profile'),
    re_path(r'^profile/(?P<category>\w+)/(?P<status>\w+)$', views.get_profile_works, name='my-profile'),
    re_path(r'^u/(?P<username>.+?)/works/(?P<category>\w+?)/$', views.get_profile_works, name='profile-works'),
    re_path(r'^u/(?P<username>.+?)/works/(?P<category>\w+?)/(?P<status>\w+)$', views.get_profile_works, name='profile-works'),
    re_path(r'^u/(?P<username>.+?)/preferences$', views.get_profile_preferences, name='profile-preferences'),
    re_path(r'^profile/friendlist$', views.get_profile_friendlist, name='profile-friendlist'),
    re_path(r'^u/(?P<username>.+?)/?$', views.get_profile_works, name='profile'),

    re_path(r'^reco/$', views.get_reco, name='reco'),
    re_path(r'^artists/$', views.ArtistList.as_view(), name='artist-list'),
    re_path(r'^artist/(?P<pk>\d+)$', views.ArtistDetail.as_view(), name='artist-detail'),
    re_path(r'^artist/(?P<artist_id>\d+)/add/(?P<work_id>\d+)$', views.add_pairing, name='add-pairing'),
    re_path(r'^vote/(?P<work_id>\d+)$', views.rate_work, name='vote'),
    re_path(r'^add_friend/(?P<username>.+?)$', views.add_friend, name='add-friend'),
    re_path(r'^del_friend/(?P<username>.+?)$', views.del_friend, name='del-friend'),
    re_path(r'^toggle-friend/(?P<username>.+?)$', views.toggle_friend, name='toggle-friend'),
    re_path(r'^settings/$', views.update_settings, name='settings'),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^about/(?P<lang>[\w-]*)$', views.about, name='about'),
    re_path(r'^faq/$', views.faq_index, name='faq'),
    re_path(r'^legal/$', views.legal_mentions, name='legal'),
    re_path(r'^cgu/$', views.MarkdownView.as_view(), kwargs={'slug': 'cgu'}, name='cgu'),

    re_path(r'^fix/$', views.fix_index, name='fix-index'),
    re_path(r'^fix/suggestion/$', views.fix_index, name='fix-index'),
    re_path(r'^fix/suggestion/(?P<suggestion_id>\d+)$', views.fix_suggestion, name='fix-suggestion'),
    re_path(r'^evidence/$', views.update_evidence, name='update-evidence'),
    re_path(r'^grid/nsfw/$', views.nsfw_grid, name='nsfw-grid'),

    # re_path(r'^lookup/$', views.lookup_work'),
    re_path(r'^top/(?P<category_slug>[\w-]+)/$', views.top, name='top'),
    re_path(r'^(?P<category>[\w-]+)/$', views.WorkList.as_view(), name='work-list'),
    re_path(r'^(?P<category>[\w-]+)/(?P<pk>\d+)$', views.WorkDetail.as_view(), name='work-detail'),
]

handler404 = views.generic_error_view(_("The page you're looking for was not found (yet?)."), 404)
handler403 = views.generic_error_view(_("You don't have access to this page."), 403)
handler400 = views.generic_error_view(_("This request is incorrect. What did you try to do?"), 400)

if DEBUG:  # https://docs.djangoproject.com/en/1.10/howto/static-files/#serving-files-uploaded-by-a-user-during-development
    import debug_toolbar

    urlpatterns += [
                       path('__debug__/', include(debug_toolbar.urls)),
                   ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
