from django.conf.urls import url

from profiles import views

urlpatterns = [
    url(r'^shared/$', views.update_shared, name='shared'),
    url(r'^nsfw/$', views.update_nsfw, name='nsfw'),
    url(r'^newsletter/$', views.update_newsletter, name='newsletter'),
    url(r'^reco_willsee/$', views.update_reco_willsee, name='reco-willsee'),
]
