# coding=utf8
from mangaki.models import Anime, Manga, Genre, Track, OST, Artist, Studio, Editor, Rating, Page, Suggestion, SearchIssue, Announcement, Recommendation, Pairing, Reference
from django.contrib import admin
from django.template.response import TemplateResponse
from django.contrib.admin import helpers


class AnimeAdmin(admin.ModelAdmin):
    search_fields = ('id', 'title')
    list_display = ('id', 'title', 'nsfw')
    list_filter = ('nsfw',)
    actions = ['make_nsfw', 'make_sfw']

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
    actions = ['make_nsfw', 'make_sfw', 'merge']

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

    def merge(self, request, queryset):
        queryset = queryset.order_by('id')
        opts = self.model._meta
        if request.POST.get('post'):
            chosen_id = int(request.POST.get('chosen_id'))
            for obj in queryset:
                if obj.id != chosen_id:
                    for rating in Rating.objects.filter(work=obj).select_related('user'):
                        # S'il n'a pas déjà voté pour l'autre
                        if Rating.objects.filter(user=rating.user, work__id=chosen_id).count() == 0:
                            rating.work_id = chosen_id
                            rating.save()
                        else:
                            rating.delete()
                    self.message_user(request, "%s a bien été supprimé." % obj.title)
                    obj.delete()
            return None
        deletable_objects = []
        for obj in queryset:
            deletable_objects.append(Rating.objects.filter(work=obj)[:10])
        context = {
            'queryset': queryset,
            'opts': opts,
            'deletable_objects': deletable_objects,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME
        }
        return TemplateResponse(request, 'admin/merge_selected_confirmation.html', context)
    merge.short_description = "Fusionner les mangas sélectionnés"


class GenreAdmin(admin.ModelAdmin):
    pass


class TrackAdmin(admin.ModelAdmin):
    pass


class OSTAdmin(admin.ModelAdmin):
    pass


class ArtistAdmin(admin.ModelAdmin):
    search_fields = ('id', 'first_name', 'last_name')


class StudioAdmin(admin.ModelAdmin):
    pass


class EditorAdmin(admin.ModelAdmin):
    pass


class RatingAdmin(admin.ModelAdmin):
    pass


class PageAdmin(admin.ModelAdmin):
    pass


class SuggestionAdmin(admin.ModelAdmin):
    list_display = ('work', 'problem', 'date', 'user', 'is_checked')
    list_filter = ('problem',)
    readonly_fields = ('current_work_data',)
    actions = ['check_suggestions', 'uncheck_suggestions']

    def check_suggestions(self, request, queryset):
        rows_updated = queryset.update(is_checked=True)
        users_list = []
        for suggestion in queryset:
            if suggestion.problem == 'ref':  # Reference suggestion
                reference, created = Reference.objects.get_or_create(work=suggestion.work, url=suggestion.message)
                reference.suggestions.add(suggestion)
            if suggestion.user not in users_list:
                users_list.append(suggestion.user)
                suggestion.update_scores()
        if rows_updated == 1:
            message_bit = "1 suggestion"
        else:
            message_bit = "%s suggestions" % rows_updated
        self.message_user(request, "La validation de %s a réussi." % message_bit)
    check_suggestions.short_description = "Valider les suggestions sélectionnées"

    def uncheck_suggestions(self, request, queryset):
        rows_updated = queryset.update(is_checked=False)
        users_list = []
        for suggestion in queryset:
            if suggestion.user not in users_list:
                users_list.append(suggestion.user)
                suggestion.update_scores()
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


class RecommendationAdmin(admin.ModelAdmin):
    pass


class PairingAdmin(admin.ModelAdmin):
    list_display = ('artist', 'work', 'date', 'user', 'is_checked')
    actions = ['make_director', 'make_composer', 'make_author']

    def make_director(self, request, queryset):
        rows_updated = 0
        for pairing in queryset:
            if Anime.objects.filter(id=pairing.work.id).update(director=pairing.artist):
                pairing.is_checked = True
                pairing.save()
                rows_updated += 1
        if rows_updated == 1:
            message_bit = "1 réalisateur a"
        else:
            message_bit = "%s réalisateurs ont" % rows_updated
        self.message_user(request, "%s été mis à jour." % message_bit)
    make_director.short_description = "Valider les appariements sélectionnés pour réalisation"

    def make_composer(self, request, queryset):
        rows_updated = 0
        for pairing in queryset:
            if Anime.objects.filter(id=pairing.work.id).update(composer=pairing.artist):
                pairing.is_checked = True
                pairing.save()
                rows_updated += 1
        if rows_updated == 1:
            message_bit = "1 compositeur a"
        else:
            message_bit = "%s compositeurs ont" % rows_updated
        self.message_user(request, "%s été mis à jour." % message_bit)
    make_composer.short_description = "Valider les appariements sélectionnés pour composition"

    def make_author(self, request, queryset):
        rows_updated = 0
        for pairing in queryset:
            if Anime.objects.filter(id=pairing.work.id).update(author=pairing.artist):
                pairing.is_checked = True
                pairing.save()
                rows_updated += 1
        if rows_updated == 1:
            message_bit = "1 auteur a"
        else:
            message_bit = "%s auteurs ont" % rows_updated
        self.message_user(request, "%s été mis à jour." % message_bit)
    make_author.short_description = "Valider les appariements sélectionnés pour écriture"


class ReferenceAdmin(admin.ModelAdmin):
    list_display = ['work', 'url']


admin.site.register(Anime, AnimeAdmin)
admin.site.register(Manga, MangaAdmin)
admin.site.register(Genre, GenreAdmin)
admin.site.register(Track, TrackAdmin)
admin.site.register(OST, OSTAdmin)
admin.site.register(Artist, ArtistAdmin)
admin.site.register(Studio, StudioAdmin)
admin.site.register(Editor, EditorAdmin)
admin.site.register(Rating, RatingAdmin)
admin.site.register(Page, PageAdmin)
admin.site.register(Suggestion, SuggestionAdmin)
admin.site.register(SearchIssue, SearchIssueAdmin)
admin.site.register(Announcement, AnnouncementAdmin)
admin.site.register(Recommendation, RecommendationAdmin)
admin.site.register(Pairing, PairingAdmin)
admin.site.register(Reference, ReferenceAdmin)
