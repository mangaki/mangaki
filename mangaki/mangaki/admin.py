import time
import logging

from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import helpers
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Count, Case, When, Value, IntegerField
from django.db.models.aggregates import Max
from django.template.response import TemplateResponse
from django.utils.html import format_html, format_html_join
from django.utils import timezone

from mangaki.models import (
    Work, TaggedWork, WorkTitle, Genre, Track, Tag, Artist, Studio, Editor, Rating, Page,
    Suggestion, SearchIssue, Announcement, Recommendation, Pairing, Reference, Top, Ranking,
    Role, Staff, FAQTheme,
    FAQEntry, ColdStartRating, Trope, Language,
    ExtLanguage, WorkCluster
)
from mangaki.utils.anidb import client
from mangaki.utils.db import get_potential_posters

from collections import defaultdict
from enum import Enum


class MergeType(Enum):
    INFO_ONLY = (0, 'black')
    JUST_CONFIRM = (1, 'green')
    CHOICE_REQUIRED = (2, 'red')

    def __init__(self, priority, row_color):
        self.priority = priority
        self.row_color = row_color


def overwrite_fields(final_work, request):
    for field in request.POST.get('fields_to_choose').split(','):
        if request.POST.get(field) != 'None':
            setattr(final_work, field, request.POST.get(field))
    final_work.save()


def redirect_ratings(works_to_merge, final_work):
    # Get all IDs of considered ratings
    get_id_of_rating = {}
    for rating_id, user_id, date in Rating.objects.filter(work__in=works_to_merge).values_list('id', 'user_id', 'date'):
        get_id_of_rating[(user_id, date)] = rating_id
    # What is the latest rating of every user? (N. B. – latest may be null)
    kept_rating_ids = []
    for rating in Rating.objects.filter(work__in=works_to_merge).values('user_id').annotate(latest=Max('date')):
        user_id = rating['user_id']
        date = rating['latest']
        kept_rating_ids.append(get_id_of_rating[(user_id, date)])
    Rating.objects.filter(work__in=works_to_merge).exclude(id__in=kept_rating_ids).delete()
    Rating.objects.filter(id__in=kept_rating_ids).update(work_id=final_work.id)


def redirect_staff(works_to_merge, final_work):
    final_work_staff = set()
    kept_staff_ids = []
    # Only one query: put final_work's Staff objects first in the list
    queryset = (Staff.objects.filter(work__in=works_to_merge)
                             .annotate(belongs_to_final_work=Case(
                                        When(work_id=final_work.id, then=Value(1)),
                                        default=Value(0), output_field=IntegerField()))
                             .order_by('-belongs_to_final_work')
                             .values_list('id', 'work_id', 'artist_id', 'role_id'))
    for staff_id, work_id, artist_id, role_id in queryset:
        if work_id == final_work.id:  # This condition will be met for the first iterations
            final_work_staff.add((artist_id, role_id))
        elif (artist_id, role_id) not in final_work_staff:  # Now we are sure we know every staff of the final work
            kept_staff_ids.append(staff_id)
    Staff.objects.filter(work__in=works_to_merge).exclude(work_id=final_work.id).exclude(id__in=kept_staff_ids).delete()
    Staff.objects.filter(id__in=kept_staff_ids).update(work_id=final_work.id)


def redirect_related_objects(works_to_merge, final_work):
    genres = sum((list(work.genre.all()) for work in works_to_merge), [])
    work_ids = [work.id for work in works_to_merge]
    final_work.genre.add(*genres)
    Trope.objects.filter(origin_id__in=work_ids).update(origin_id=final_work.id)
    for model in [WorkTitle, TaggedWork, Suggestion, Recommendation, Pairing, Reference, ColdStartRating]:
        model.objects.filter(work_id__in=work_ids).update(work_id=final_work.id)
    Work.objects.filter(id__in=work_ids).exclude(id=final_work.id).update(redirect=final_work)


def create_merge_form(works_to_merge_qs):
    work_dicts_to_merge = list(works_to_merge_qs.values())
    rows = defaultdict(list)
    for work_dict in work_dicts_to_merge:
        for field in work_dict:
            rows[field].append(work_dict[field])
    fields_to_choose = []
    template_rows = []
    for field in rows:
        choices = rows[field]
        suggested = None
        if field in {'sum_ratings', 'nb_ratings', 'nb_likes', 'nb_dislikes', 'controversy'}:
            merge_type = MergeType.INFO_ONLY
        elif all(choice == choices[0] for choice in choices):  # All equal
            merge_type = MergeType.JUST_CONFIRM
            suggested = choices[0]
        elif sum(not choice or choice == 'Inconnu' for choice in choices) == len(choices) - 1:  # All empty but one
            merge_type = MergeType.JUST_CONFIRM
            suggested = [choice for choice in choices if choice and choice != 'Inconnu'][0]  # Remaining one
        else:
            merge_type = MergeType.CHOICE_REQUIRED
        template_rows.append({
            'field': field,
            'choices': choices,
            'merge_type': merge_type,
            'suggested': suggested,
            'color': merge_type.row_color,
        })
        if field != 'id' and merge_type != MergeType.INFO_ONLY:
            fields_to_choose.append(field)
    template_rows.sort(key=lambda row: row['merge_type'].priority, reverse=True)
    rating_samples = [(Rating.objects.filter(work_id=work_dict['id']).count(),
                       Rating.objects.filter(work_id=work_dict['id'])[:10]) for work_dict in work_dicts_to_merge]
    return fields_to_choose, template_rows, rating_samples


@transaction.atomic  # In case trouble happens
def merge_works(request, selected_queryset):
    if selected_queryset.model == WorkCluster:  # Author is reviewing an existing WorkCluster
        from_cluster = True
        cluster = selected_queryset.first()
        works_to_merge_qs = cluster.works.order_by('id').prefetch_related('rating_set', 'genre')
        works_to_merge = list(works_to_merge_qs)
    else:  # Author is merging those works from a Work queryset
        from_cluster = False
        cluster = WorkCluster(user=request.user, checker=request.user)
        cluster.save()  # Otherwise we cannot add works
        works_to_merge_qs = selected_queryset.prefetch_related('rating_set', 'genre')
        works_to_merge = list(works_to_merge_qs)
        cluster.works.add(*works_to_merge)
    if request.POST.get('confirm'):  # Merge has been confirmed
        final_id = int(request.POST.get('id'))
        final_work = Work.objects.get(id=final_id)
        overwrite_fields(final_work, request)
        redirect_ratings(works_to_merge, final_work)
        redirect_staff(works_to_merge, final_work)
        redirect_related_objects(works_to_merge, final_work)
        WorkCluster.objects.filter(id=cluster.id).update(
            checker=request.user, resulting_work=final_work, merged_on=timezone.now(), status='accepted')
        return len(works_to_merge), final_work, None

    fields_to_choose, template_rows, rating_samples = create_merge_form(works_to_merge_qs)
    context = {
        'fields_to_choose': ','.join(fields_to_choose),
        'template_rows': template_rows,
        'rating_samples': rating_samples,
        'queryset': selected_queryset,
        'opts': Work._meta if not from_cluster else WorkCluster._meta,
        'action': 'merge' if not from_cluster else 'trigger_merge',
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME
    }
    return len(works_to_merge), None, TemplateResponse(request, 'admin/merge_selected_confirmation.html', context)

logger = logging.getLogger(__name__)


class TaggedWorkInline(admin.TabularInline):
    model = TaggedWork
    fields = ('work', 'tag', 'weight')


class StaffInline(admin.TabularInline):
    model = Staff
    fields = ('role', 'artist')
    raw_id_fields = ('artist',)


class WorkTitleInline(admin.TabularInline):
    model = WorkTitle
    fields = ('title', 'language', 'type')


class AniDBaidListFilter(admin.SimpleListFilter):
    title = 'AniDB aid'
    parameter_name = 'AniDB aid'

    def lookups(self, request, model_admin):
        return ('Vrai', 'Oui'), ('Faux', 'Non')

    def queryset(self, request, queryset):
        if self.value() == 'Faux':
            return queryset.filter(anidb_aid=0)
        elif self.value() == 'Vrai':
            return queryset.exclude(anidb_aid=0)
        else:
            return queryset


@admin.register(FAQTheme)
class FAQAdmin(admin.ModelAdmin):
    ordering = ('order',)
    search_fields = ('theme',)
    list_display = ('theme', 'order')


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    search_fields = ('id', 'title')
    list_display = ('id', 'category', 'title', 'nsfw')
    list_filter = ('category', 'nsfw', AniDBaidListFilter,)
    raw_id_fields = ('redirect',)
    actions = ['make_nsfw', 'make_sfw', 'refresh_work_from_anidb', 'merge', 'refresh_work', 'update_tags_via_anidb']
    inlines = [StaffInline, WorkTitleInline, TaggedWorkInline]
    readonly_fields = (
        'sum_ratings',
        'nb_ratings',
        'nb_likes',
        'nb_dislikes',
        'controversy',
    )

    def make_nsfw(self, request, queryset):
        rows_updated = queryset.update(nsfw=True)
        if rows_updated == 1:
            message_bit = "1 œuvre est"
        else:
            message_bit = "%s œuvres sont" % rows_updated
        self.message_user(request, "%s désormais NSFW." % message_bit)

    make_nsfw.short_description = "Rendre NSFW les œuvres sélectionnées"

    # FIXME : https://github.com/mangaki/mangaki/issues/205
    def update_tags_via_anidb(self, request, queryset):
        if request.POST.get("post"):
            kept_ids = request.POST.getlist('checks')
            for anime_id in kept_ids:
                anime = Work.objects.get(id=anime_id)

                retrieved_tags = anime.retrieve_tags(client)
                deleted_tags = retrieved_tags["deleted_tags"]
                added_tags = retrieved_tags["added_tags"]
                updated_tags = retrieved_tags["updated_tags"]

                tags = deleted_tags
                tags.update(added_tags)
                tags.update(updated_tags)

                anime.update_tags(tags)

            self.message_user(request, "Modifications sur les tags faites")
            return None

        for anime in queryset.select_related("category"):
            if anime.category.slug != 'anime':
                self.message_user(request,
                                  "%s n'est pas un anime. La recherche des tags via AniDB n'est possible que pour les "
                                  "animes " % anime.title)
                self.message_user(request, "Vous avez un filtre à votre droite pour avoir les animes avec un anidb_aid")
                return None
            elif not anime.anidb_aid:
                self.message_user(
                    request,
                    "%s n'a pas de lien actuel avec la base d'aniDB (pas d'anidb_aid)" % anime.title)
                self.message_user(
                    request,
                    "Vous avez un filtre à votre droite pour avoir les animes avec un anidb_aid")
                return None

        all_information = {}
        for anime in queryset:
            retrieved_tags = anime.retrieve_tags(client)
            deleted_tags = retrieved_tags["deleted_tags"]
            added_tags = retrieved_tags["added_tags"]
            updated_tags = retrieved_tags["updated_tags"]
            kept_tags = retrieved_tags["kept_tags"]

            all_information[anime.id] = {'title': anime.title, 'deleted_tags': deleted_tags.items(),
                                         'added_tags': added_tags.items(), 'updated_tags': updated_tags.items(),
                                         "kept_tags": kept_tags.items()}

        context = {
            'all_information': all_information.items(),
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
        }
        return TemplateResponse(request, "admin/update_tags_via_anidb.html", context)

    update_tags_via_anidb.short_description = "Mettre à jour les tags des œuvres depuis AniDB"

    def make_sfw(self, request, queryset):
        rows_updated = queryset.update(nsfw=False)
        if rows_updated == 1:
            message_bit = "1 œuvre n'est"
        else:
            message_bit = "%s œuvres ne sont" % rows_updated
        self.message_user(request, "%s désormais plus NSFW." % message_bit)

    make_sfw.short_description = "Rendre SFW les œuvres sélectionnées"

    @transaction.atomic
    def refresh_work_from_anidb(self, request, queryset):
        works = queryset.all()

        if not all(work.anidb_aid for work in works):
            offending_works = [work for work in works if not work.anidb_aid]
            self.message_user(request,
                              "Certains de vos choix ne possèdent pas d'identifiant AniDB. "
                              "Leur rafraichissement a été omis. (Détails: {})"
                              .format(", ".join(map(lambda w: w.title, offending_works))),
                              level=messages.WARNING)

        for index, work in enumerate(works, start=1):
            if work.anidb_aid:
                logger.info('Refreshing {} from AniDB.'.format(work))
                client.get_or_update_work(work.anidb_aid)
                if index % 25 == 0:
                    logger.info('(AniDB refresh): Sleeping...')
                    time.sleep(1)  # Don't spam AniDB.

        self.message_user(request,
                          "Le rafraichissement des œuvres a été effectué avec succès.")

    refresh_work_from_anidb.short_description = "Rafraîchir les œuvres depuis AniDB"

    def merge(self, request, queryset):
        nb_merged, final_work, response = merge_works(request, queryset)
        if response is None:  # Confirmed
            self.message_user(request, format_html('La fusion de {:d} œuvres vers <a href="{:s}">{:s}</a> a bien été effectuée.'
                .format(nb_merged, final_work.get_absolute_url(), final_work.title)))
        return response

    merge.short_description = "Fusionner les œuvres sélectionnées"

    def refresh_work(self, request, queryset):
        if request.POST.get('confirm'):  # Confirmed
            downloaded_titles = []
            for obj in queryset:
                chosen_poster = request.POST.get('chosen_poster_{:d}'.format(obj.id))
                if not chosen_poster:
                    continue
                if obj.retrieve_poster(chosen_poster):
                    downloaded_titles.append(obj.title)
            if downloaded_titles:
                self.message_user(
                    request,
                    "Des posters ont été trouvés pour les anime suivants : %s." % ', '.join(downloaded_titles))
            else:
                self.message_user(request, "Aucun poster n'a été trouvé, essayez de changer le titre.")
            return None
        bundle = []
        for work in queryset:
            bundle.append((work.id, work.title, get_potential_posters(work)))
        context = {
            'queryset': queryset,
            'bundle': bundle,
            'opts': self.model._meta,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME
        }
        return TemplateResponse(request, 'admin/refresh_poster_confirmation.html', context)

    refresh_work.short_description = "Mettre à jour la fiche de l'anime (poster)"


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    search_fields = ('id', 'name')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("title",)
    readonly_fields = ("nb_works_linked",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(works_linked=Count('work'))

    def nb_works_linked(self, obj):
        return obj.works_linked

    nb_works_linked.short_description = 'Nombre d\'œuvres liées au tag'


@admin.register(TaggedWork)
class TaggedWorkAdmin(admin.ModelAdmin):
    search_fields = ('work', 'tag')


@admin.register(WorkCluster)
class WorkClusterAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_work_titles', 'resulting_work', 'reported_on', 'merged_on', 'checker', 'status')
    raw_id_fields = ('user', 'works', 'checker', 'resulting_work')
    actions = ('trigger_merge', 'reject')

    def trigger_merge(self, request, queryset):
        cluster = queryset.first()
        nb_merged, final_work, response = merge_works(request, queryset)
        if response is None:
            self.message_user(request, format_html('La fusion de {:d} œuvres vers <a href="{:s}">{:s}</a> a bien été effectuée.'
                .format(nb_merged, final_work.get_absolute_url(), final_work.title)))
        return response

    trigger_merge.short_description = "Fusionner les œuvres de ce cluster"

    def reject(self, request, queryset):
        rows_updated = queryset.update(status='rejected')
        if rows_updated == 1:
            message_bit = "1 cluster"
        else:
            message_bit = "%s clusters" % rows_updated
        self.message_user(request, "Le rejet de %s a été réalisé avec succès." % message_bit)

    reject.short_description = "Rejeter les clusters sélectionnés"

    def get_work_titles(self, obj):
        cluster_works = list(Work.all_objects.filter(workcluster=obj))
        if cluster_works:
            def get_admin_url(work):
                return reverse('admin:mangaki_work_change', args=(work.id,))
            return (
                '<ul>' +
                format_html_join('', '<li>{} (<a href="{}">{}</a>)</li>',
                    ((work.title, get_admin_url(work), work.id) for work in cluster_works)) +
                '</ul>'
            )
        else:
            return '(all deleted)'

    get_work_titles.allow_tags = True


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ('work', 'problem', 'date', 'user', 'is_checked')
    list_filter = ('problem',)
    actions = ['check_suggestions', 'uncheck_suggestions']
    raw_id_fields = ('work',)

    def view_on_site(self, obj):
        return obj.work.get_absolute_url()

    def check_suggestions(self, request, queryset):
        rows_updated = queryset.update(is_checked=True)
        for suggestion in queryset:
            if suggestion.problem == 'ref':  # Reference suggestion
                reference, created = Reference.objects.get_or_create(work=suggestion.work, url=suggestion.message)
                reference.suggestions.add(suggestion)
        if rows_updated == 1:
            message_bit = "1 suggestion"
        else:
            message_bit = "%s suggestions" % rows_updated
        self.message_user(request, "La validation de %s a été réalisé avec succès." % message_bit)

    check_suggestions.short_description = "Valider les suggestions sélectionnées"

    def uncheck_suggestions(self, request, queryset):
        rows_updated = queryset.update(is_checked=False)
        if rows_updated == 1:
            message_bit = "1 suggestion"
        else:
            message_bit = "%s suggestions" % rows_updated
        self.message_user(request, "L'invalidation de %s a été réalisé avec succès." % message_bit)

    uncheck_suggestions.short_description = "Invalider les suggestions sélectionnées"


@admin.register(SearchIssue)
class SearchIssueAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'user')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    exclude = ('title',)


@admin.register(Pairing)
class PairingAdmin(admin.ModelAdmin):
    list_display = ('artist', 'work', 'date', 'user', 'is_checked')
    actions = ['make_director', 'make_composer', 'make_author']

    def make_director(self, request, queryset):
        rows_updated = 0
        director = Role.objects.get(slug='director')
        for pairing in queryset:
            _, created = Staff.objects.get_or_create(work_id=pairing.work_id, artist_id=pairing.artist_id,
                                                     role=director)
            if created:
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
        composer = Role.objects.get(slug='composer')
        for pairing in queryset:
            _, created = Staff.objects.get_or_create(work_id=pairing.work_id, artist_id=pairing.artist_id,
                                                     role=composer)
            if created:
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
        author = Role.objects.get(slug='author')
        for pairing in queryset:
            _, created = Staff.objects.get_or_create(work_id=pairing.work_id, artist_id=pairing.artist_id, role=author)
            if created:
                pairing.is_checked = True
                pairing.save()
                rows_updated += 1
        if rows_updated == 1:
            message_bit = "1 auteur a"
        else:
            message_bit = "%s auteurs ont" % rows_updated
        self.message_user(request, "%s été mis à jour." % message_bit)

    make_author.short_description = "Valider les appariements sélectionnés pour écriture"


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    list_display = ['work', 'url']


class RankingInline(admin.TabularInline):
    model = Ranking
    fields = ('content_type', 'object_id', 'name', 'score', 'nb_ratings', 'nb_stars',)
    readonly_fields = ('name',)

    def name(self, instance):
        return str(instance.content_object)


@admin.register(Top)
class TopAdmin(admin.ModelAdmin):
    inlines = [
        RankingInline,
    ]
    readonly_fields = ('category', 'date',)

    def has_add_permission(self, request):
        return False


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    model = Role
    prepopulated_fields = {'slug': ('name',)}


admin.site.register(Genre)
admin.site.register(Track)
admin.site.register(Studio)
admin.site.register(Editor)
admin.site.register(Rating)
admin.site.register(Page)
admin.site.register(FAQEntry)
admin.site.register(Recommendation)
admin.site.register(ColdStartRating)
admin.site.register(Trope)
admin.site.register(Language)
admin.site.register(ExtLanguage)
