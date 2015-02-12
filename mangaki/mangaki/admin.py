# coding=utf8
from mangaki.models import Anime, Track, OST, Artist, Rating, Page, Suggestion
from django.forms import Textarea
from django.db import models
from django.contrib import admin, messages

class AnimeAdmin(admin.ModelAdmin):
    search_fields = ('id', 'title')
    list_display = ('id', 'title', 'nsfw')
    list_filter = ('nsfw',)

class TrackAdmin(admin.ModelAdmin):
    pass

class OSTAdmin(admin.ModelAdmin):
    pass

class ArtistAdmin(admin.ModelAdmin):
    pass

class RatingAdmin(admin.ModelAdmin):
    pass

class PageAdmin(admin.ModelAdmin):
    pass

class SuggestionAdmin(admin.ModelAdmin):
    list_display = ('work', 'problem', 'date', 'user', 'is_checked')
    list_filter = ('problem',)

admin.site.register(Anime, AnimeAdmin)
admin.site.register(Track, TrackAdmin)
admin.site.register(OST, OSTAdmin)
admin.site.register(Artist, ArtistAdmin)
admin.site.register(Rating, RatingAdmin)
admin.site.register(Suggestion, SuggestionAdmin)
