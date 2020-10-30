import time
import logging

from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import helpers
from django.urls import reverse
from django.db import transaction
from django.db.models import Count
from django.template.response import TemplateResponse
from django.utils.html import format_html, format_html_join

from mangaki.models import (
    Work, TaggedWork, WorkTitle, Genre, Track, Tag, Artist, Studio, Editor, Rating, Page,
    Suggestion, Evidence, Announcement, Recommendation, Pairing, Reference, Top, Ranking,
    Role, Staff, FAQTheme,
    FAQEntry, Trope, Language,
    ExtLanguage, WorkCluster,
    UserBackgroundTask,
    ActionType,
    get_field_changeset
)
from mangaki.utils.anidb import AniDBTag, client, diff_between_anidb_and_local_tags
from mangaki.utils.db import get_potential_posters

from collections import defaultdict
from enum import Enum

from mangaki.utils.work_merge import WorkClusterMergeHandler

ActionTypeColors = {
    ActionType.DO_NOTHING: 'black',  # INFO_ONLY
    ActionType.JUST_CONFIRM: 'green',
    ActionType.CHOICE_REQUIRED: 'red'
}


class MergeErrors(Enum):
    NO_ID = 'no ID'
    FIELDS_MISSING = 'missing fields'
    NOT_ENOUGH_WORKS = 'not enough works'


def handle_merge_errors(response, request, final_work, nb_merged,
                        message_user):
    if response == MergeErrors.NO_ID:
        message_user(request,
                     "Aucun ID n'a été fourni pour la fusion.",
                     level=messages.ERROR)
    if response == MergeErrors.FIELDS_MISSING:
        message_user(request,
                     """Un ou plusieurs des champs requis n'ont pas été remplis.
                          (Détails: {})""".format(", ".join(final_work)),
                     level=messages.ERROR)
    if response == MergeErrors.NOT_ENOUGH_WORKS:
        message_user(request,
                     "Veuillez sélectionner au moins 2 œuvres à fusionner.",
                     level=messages.WARNING)
    if response is None:  # Confirmed
        message_user(request,
                     format_html('La fusion de {:d} œuvres vers <a href="{:s}">{:s}</a> a bien été effectuée.'
                                 .format(nb_merged, final_work.get_absolute_url(), final_work.title)))


def create_merge_form(works_to_merge_qs):
    work_dicts_to_merge = list(works_to_merge_qs.values())
    field_changeset = get_field_changeset(work_dicts_to_merge)

    fields_to_choose = []
    fields_required = []
    template_rows = []

    suggestions = {}
    for field, choices, action, suggested, _ in field_changeset:
        suggestions[field] = suggested
        template_rows.append({
            'field': field,
            'choices': choices,
            'action_type': action,
            'suggested': suggested,
            'color': ActionTypeColors[action],
        })

        if field != 'id' and action != ActionType.DO_NOTHING:
            fields_to_choose.append(field)

        if action == ActionType.CHOICE_REQUIRED:
            fields_required.append(field)

    template_rows.sort(key=lambda row: int(row['action_type']), reverse=True)
    rating_samples = [(Rating.objects.filter(work_id=work_dict['id']).count(),
                       Rating.objects.filter(work_id=work_dict['id'])[:10]) for work_dict in work_dicts_to_merge]  # FIXME: too many queries
    return fields_to_choose, fields_required, template_rows, rating_samples, suggestions


@transaction.atomic  # In case trouble happens
def merge_works(request, selected_queryset, force=False):
    user = request.user if request else None
    if selected_queryset.model == WorkCluster:  # Author is reviewing an existing WorkCluster
        from_cluster = True
        cluster = selected_queryset.first()
        works_to_merge_qs = cluster.works.order_by('id').prefetch_related('rating_set', 'genre')
    else:  # Author is merging those works from a Work queryset
        from_cluster = False
        works_to_merge_qs = selected_queryset.order_by('id').prefetch_related('rating_set', 'genre')
    nb_works_to_merge = works_to_merge_qs.count()

    if request and request.POST.get('confirm'):  # Merge has been confirmed
        rich_context = request.POST
    else:
        fields_to_choose, fields_required, template_rows, rating_samples, suggestions = create_merge_form(works_to_merge_qs)
        context = {
            'fields_to_choose': ','.join(fields_to_choose),
            'fields_required': ','.join(fields_required),
            'template_rows': template_rows,
            'rating_samples': rating_samples,
            'queryset': selected_queryset,
            'opts': Work._meta if not from_cluster else WorkCluster._meta,
            'action': 'merge' if not from_cluster else 'trigger_merge',
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME
        }
        if all(field in suggestions for field in fields_required):
            rich_context = dict(context)
            for field in suggestions:
                rich_context[field] = suggestions[field]
            if force:
                rich_context['confirm'] = True

    if rich_context.get('confirm'):  # Merge has been confirmed
        works_to_merge = list(works_to_merge_qs)
        if not from_cluster:
            cluster = WorkCluster(user=user, checker=user)
            cluster.save()  # Otherwise we cannot add works
            cluster.works.add(*works_to_merge)

        # Happens when no ID was provided
        if not rich_context.get('id'):
            return None, None, MergeErrors.NO_ID

        final_id = int(rich_context.get('id'))
        final_work = Work.objects.get(id=final_id)

        # Notice how `cluster` always exist in this scope.

        # noinspection PyUnboundLocalVariable
        merge_handler = WorkClusterMergeHandler(cluster,
                                                works_to_merge,
                                                final_work)

        missing_required_fields = merge_handler.overwrite_fields(
            set(filter(None, rich_context.get('fields_to_choose').split(','))),
            set(filter(None, rich_context.get('fields_required').split(','))),
            rich_context)

        # Happens when a required field was left empty
        if missing_required_fields:
            return None, missing_required_fields, MergeErrors.FIELDS_MISSING

        merge_handler.perform_redirections()
        merge_handler.accept_cluster(user)
        return len(works_to_merge), merge_handler.target_work, None

    # Just show a warning if only one work was checked
    if nb_works_to_merge < 2:
        return None, None, MergeErrors.NOT_ENOUGH_WORKS

    return nb_works_to_merge, None, TemplateResponse(request, 'admin/merge_selected_confirmation.html', context)


logger = logging.getLogger(__name__)


class TaggedWorkInline(admin.TabularInline):
    model = TaggedWork
    fields = ('work', 'tag', 'weight')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('work', 'tag')


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
    search_fields = ('id', 'title', 'worktitle__title')
    list_display = ('id', 'category', 'title', 'nsfw')
    list_filter = ('category', 'nsfw', AniDBaidListFilter)
    raw_id_fields = ('redirect',)
    actions = ['make_nsfw', 'make_sfw', 'refresh_work_from_anidb', 'merge',
               'refresh_work', 'update_tags_via_anidb', 'change_title']
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

    def update_tags_via_anidb(self, request, queryset):
        works = queryset.all()

        if request.POST.get('confirm'):  # Updating tags has been confirmed
            to_update_work_ids = set(map(int, request.POST.getlist('to_update_work_ids')))
            nb_updates = len(to_update_work_ids)

            work_ids = list(map(int, request.POST.getlist('work_ids')))

            tag_titles = request.POST.getlist('tag_titles')
            tag_weights = list(map(int, request.POST.getlist('weights')))
            tag_anidb_tag_ids = list(map(int, request.POST.getlist('anidb_tag_ids')))
            tags = list(map(AniDBTag, tag_titles, tag_weights, tag_anidb_tag_ids))

            # Checkboxes to know which tags have to be kept regardless of their pending status
            tag_checkboxes = request.POST.getlist('tag_checkboxes')
            tags_to_process = set(tuple(map(int, tag_checkbox.split(':'))) for tag_checkbox in tag_checkboxes)

            # Make a dict with work_id -> tags to keep
            tags_final = {}
            for index, work_id in enumerate(work_ids):
                if work_id not in to_update_work_ids:
                    continue
                if work_id not in tags_final:
                    tags_final[work_id] = []
                if (work_id, tags[index].anidb_tag_id) in tags_to_process:
                    tags_final[work_id].append(tags[index])

            # Process selected tags for works that have been selected
            for work in works:
                if work.id in to_update_work_ids:
                    client.update_tags(work, tags_final[work.id])

            if nb_updates == 0:
                self.message_user(request,
                                  "Aucune oeuvre n'a été marquée comme devant être mise à jour.",
                                  level=messages.WARNING)
            elif nb_updates == 1:
                self.message_user(request,
                                  "Mise à jour des tags effectuée pour une œuvre.")
            else:
                self.message_user(request,
                                  "Mise à jour des tags effectuée pour {} œuvres.".format(nb_updates))
            return None

        # Check for works with missing AniDB AID
        if not all(work.anidb_aid for work in works):
            self.message_user(request,
                              """Certains de vos choix ne possèdent pas d'identifiant AniDB.
            Le rafraichissement de leurs tags a été omis. (Détails: {})"""
                              .format(", ".join(map(lambda w: w.title,
                                                    filter(lambda w: not w.anidb_aid, works)))),
                              level=messages.WARNING)

        # Retrieve and send tags information to the appropriate form
        all_information = {}
        for index, work in enumerate(works, start=1):
            if work.anidb_aid:
                if index % 25 == 0:
                    logger.info('(AniDB refresh): Sleeping...')
                    time.sleep(1)  # Don't spam AniDB.

                anidb_tags = client.get_tags(anidb_aid=work.anidb_aid)
                tags_diff = diff_between_anidb_and_local_tags(work, anidb_tags)
                tags_count = 0

                for tags_info in tags_diff.values():
                    tags_count += len(tags_info)

                if tags_count > 0:
                    all_information[work.id] = {
                        'title': work.title,
                        'deleted_tags': tags_diff["deleted_tags"],
                        'added_tags': tags_diff["added_tags"],
                        'updated_tags': tags_diff["updated_tags"],
                        'kept_tags': tags_diff["kept_tags"]
                    }

        if all_information:
            context = {
                'all_information': all_information.items(),
                'queryset': queryset,
                'opts': TaggedWork._meta,
                'action': 'update_tags_via_anidb',
                'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME
            }
            return TemplateResponse(request, "admin/update_tags_via_anidb.html", context)
        else:
            self.message_user(request,
                              "Aucune des œuvres sélectionnées n'a subit de mise à jour des tags chez AniDB.",
                              level=messages.WARNING)
            return None

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

        # Check for works with missing AniDB AID
        offending_works = []
        if not all(work.anidb_aid for work in works):
            offending_works = [work for work in works if not work.anidb_aid]
            self.message_user(request,
                              "Certains de vos choix ne possèdent pas d'identifiant AniDB. "
                              "Leur rafraichissement a été omis. (Détails: {})"
                              .format(", ".join(map(lambda w: w.title, offending_works))),
                              level=messages.WARNING)

        # Check for works that have a duplicate AniDB AID
        aids_with_works = defaultdict(list)
        for work in works:
            if work.anidb_aid:
                aids_with_works[work.anidb_aid].append(work)

        aids_with_potdupe_works = defaultdict(list)
        for work in Work.objects.filter(anidb_aid__in=aids_with_works.keys()):
            aids_with_potdupe_works[work.anidb_aid].append(work)

        works_with_conflicting_anidb_aid = []
        for anidb_aid, potdupe_works in aids_with_potdupe_works.items():
            if len(potdupe_works) > 1:
                works_with_conflicting_anidb_aid.extend(aids_with_works[anidb_aid])

                # Alert the user for each work he selected that has a duplicate AniDB ID
                self.message_user(
                    request,
                    """Le rafraichissement de {} a été omis car d'autres œuvres possèdent
                    le même identifiant AniDB #{}. (Œuvres en conflit : {})"""
                    .format(
                        ", ".join(map(lambda w: w.title, aids_with_works[anidb_aid])),
                        anidb_aid,
                        ", ".join(map(lambda w: w.title, aids_with_potdupe_works[anidb_aid]))
                    ),
                    level=messages.WARNING
                )

        # Refresh works from AniDB
        refreshed = 0
        for index, work in enumerate(works, start=1):
            if work.anidb_aid and work not in works_with_conflicting_anidb_aid:
                logger.info('Refreshing {} from AniDB.'.format(work))
                if client.get_or_update_work(work.anidb_aid) is not None:
                    refreshed += 1
                if index % 25 == 0:
                    logger.info('(AniDB refresh): Sleeping...')
                    time.sleep(1)  # Don't spam AniDB.

        if refreshed > 0:
            self.message_user(request,
                              "Le rafraichissement de {} œuvre(s) a été effectué avec succès."
                              .format(refreshed))

    refresh_work_from_anidb.short_description = "Rafraîchir les œuvres depuis AniDB"

    def merge(self, request, queryset):
        nb_merged, final_work, response = merge_works(request, queryset)
        handle_merge_errors(response, request, final_work, nb_merged,
                            self.message_user)
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

    @transaction.atomic
    def change_title(self, request, queryset):
        if request.POST.get('confirm'):  # Changing default title has been confirmed
            work_ids = request.POST.getlist('work_ids')
            titles_ids = request.POST.getlist('title_ids')

            titles = WorkTitle.objects.filter(
                pk__in=titles_ids, work__id__in=work_ids
            ).values_list('title', 'work__title', 'work__id')

            for new_title, current_title, work_id in titles:
                if new_title != current_title:
                    Work.objects.filter(pk=work_id).update(title=new_title)

            self.message_user(request, 'Les titres ont bien été changés pour les œuvres sélectionnées.')
            return None

        work_titles = WorkTitle.objects.filter(work__in=queryset.values_list('pk', flat=True))
        full_infos = work_titles.values(
            'pk', 'title', 'language__code', 'type', 'work_id', 'work__title'
        ).order_by('title').distinct('title')

        titles = {}
        for infos in full_infos:
            if infos['work_id'] not in titles:
                titles[infos['work_id']] = {}

            titles[infos['work_id']].update({
                infos['pk']: {
                    'title': infos['title'],
                    'language': infos['language__code'] if infos['language__code'] else 'inconnu',
                    'type': infos['type'] if infos['title'] != infos['work__title'] else 'current'
                }
            })

        if titles:
            context = {
                'work_titles': titles,
                'queryset': queryset,
                'opts': Work._meta,
                'action': 'change_title',
                'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME
            }
            return TemplateResponse(request, 'admin/change_default_work_title.html', context)
        else:
            self.message_user(request,
                              'Aucune des œuvres sélectionnées ne possèdent de titre alternatif.',
                              level=messages.WARNING)
            return None

    change_title.short_description = "Changer le titre par défaut"


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
    search_fields = ('work__title', 'tag__title')


@admin.register(WorkCluster)
class WorkClusterAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_work_titles', 'resulting_work', 'reported_on', 'merged_on', 'checker', 'status', 'difficulty')
    list_filter = ('status',)
    list_select_related = ('user', 'resulting_work', 'checker')
    raw_id_fields = ('user', 'works', 'checker', 'resulting_work', 'origin')
    actions = ('trigger_merge', 'reject')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('works')

    def trigger_merge(self, request, queryset):
        nb_merged, final_work, response = merge_works(request, queryset)
        handle_merge_errors(response, request, final_work, nb_merged,
                            self.message_user)
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
        cluster_works = obj.works.all()  # Does not include redirected works
        if cluster_works:
            def get_admin_url(work):
                if work.redirect is None:
                    return reverse('admin:mangaki_work_change', args=(work.id,))
                else:
                    return '#'
            return (
                '<ul>'
                + format_html_join('', '<li>{} ({}<a href="{}">{}</a>)</li>',
                                   ((work.title, 'was ' if work.redirect is not None else '',
                                    get_admin_url(work), work.id) for work in cluster_works))
                + '</ul>'
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
    search_fields = ('work__title', 'user__username')

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
    raw_id_fields = ('work', 'suggestions')


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


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'suggestion', 'agrees', 'needs_help']


admin.site.register(Genre)
admin.site.register(Track)
admin.site.register(Studio)
admin.site.register(Editor)
admin.site.register(Rating)
admin.site.register(Page)
admin.site.register(FAQEntry)
admin.site.register(Recommendation)
admin.site.register(Trope)
admin.site.register(Language)
admin.site.register(ExtLanguage)
admin.site.register(UserBackgroundTask)
admin.site.site_header = "Administration Mangaki"
