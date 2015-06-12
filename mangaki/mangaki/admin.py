# coding=utf8
from mangaki.models import Anime, Manga, Genre, Track, OST, Artist, Rating, Page, Suggestion, SearchIssue, Announcement
from django.contrib import admin


class AnimeAdmin(admin.ModelAdmin):
    search_fields = ('id', 'title')
    list_display = ('id', 'title', 'nsfw')
    list_filter = ('nsfw',)
    actions = ['make_nsfw','make_sfw']
    def make_nsfw(self, request, queryset):
        rows_updated = queryset.update(nsfw=True)
        if rows_updated == 1:
            message_bit = "1 anime est"
        else:
            message_bit = "%s animes sont" % rows_updated
        self.message_user(request, "%s désormais NSFW." % message_bit)
    make_nsfw.short_description = "Rendre NSFW les animes sélectionnés"
    def make_sfw(self, request, queryset):
        rows_updated = queryset.update(nsfw=False)
        if rows_updated == 1:
            message_bit = "1 anime n'est"
        else:
            message_bit = "%s animes ne sont" % rows_updated
        self.message_user(request, "%s désormais plus NSFW." % message_bit)
    make_sfw.short_description = "Rendre SFW les animes sélectionnés"


class MangaAdmin(admin.ModelAdmin):
    search_fields = ('id', 'title')
    list_display = ('id', 'title', 'nsfw')
    list_filter = ('nsfw',)
    actions = ['make_nsfw','make_sfw']
    def make_nsfw(self, request, queryset):
        rows_updated = queryset.update(nsfw=True)
        if rows_updated == 1:
            message_bit = "1 manga est"
        else:
            message_bit = "%s mangas sont" % rows_updated
        self.message_user(request, "%s désormais NSFW." % message_bit)
    make_nsfw.short_description = "Rendre NSFW les mangas sélectionnés"
    def make_sfw(self, request, queryset):
        rows_updated = queryset.update(nsfw=False)
        if rows_updated == 1:
            message_bit = "1 manga n'est"
        else:
            message_bit = "%s mangas ne sont" % rows_updated
        self.message_user(request, "%s désormais plus NSFW." % message_bit)
    make_sfw.short_description = "Rendre SFW les mangas sélectionnés"


class GenreAdmin(admin.ModelAdmin):
    pass


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
    actions = ['check_suggestions','uncheck_suggestions']
    def check_suggestions(self, request, queryset):
        rows_updated = queryset.update(is_checked=True)
        if rows_updated == 1:
            message_bit = "1 suggestion"
        else:
            message_bit = "%s suggestions" % rows_updated
        self.message_user(request, "La validation de %s a réussi." % message_bit)
    check_suggestions.short_description = "Valider les suggestions sélectionnées"
    def uncheck_suggestions(self, request, queryset):
        rows_updated = queryset.update(is_checked=False)
        if rows_updated == 1:
            message_bit = "1 suggestion"
        else:
            message_bit = "%s suggestions" % rows_updated
        self.message_user(request, "L'invalidation de %s a réussi." % message_bit)
    uncheck_suggestions.short_description = "Invalider les suggestions sélectionnées"


class SearchIssueAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'user')

class AnnouncementAdmin(admin.ModelAdmin):
    exclude = ('title',)

admin.site.register(Anime, AnimeAdmin)
admin.site.register(Manga, MangaAdmin)
admin.site.register(Genre, GenreAdmin)
admin.site.register(Track, TrackAdmin)
admin.site.register(OST, OSTAdmin)
admin.site.register(Artist, ArtistAdmin)
admin.site.register(Rating, RatingAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(Suggestion, SuggestionAdmin)
admin.site.register(SearchIssue, SearchIssueAdmin)
admin.site.register(Announcement, AnnouncementAdmin)
