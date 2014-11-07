# coding=utf8
from mangaki.models import Anime, Track, OST, Artist, Rating
from django.forms import Textarea
from django.db import models
from django.contrib import admin, messages

class AnimeAdmin(admin.ModelAdmin):
    pass

class TrackAdmin(admin.ModelAdmin):
    pass

class OSTAdmin(admin.ModelAdmin):
    pass

class ArtistAdmin(admin.ModelAdmin):
    pass

class RatingAdmin(admin.ModelAdmin):
    pass

admin.site.register(Anime, AnimeAdmin)
admin.site.register(Track, TrackAdmin)
admin.site.register(OST, OSTAdmin)
admin.site.register(Artist, ArtistAdmin)
admin.site.register(Rating, RatingAdmin)
