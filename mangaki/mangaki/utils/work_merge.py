from collections import defaultdict
from enum import IntEnum

from django.db.models import Max, Case, When, Value, IntegerField
from django.utils import timezone

from mangaki.models import (
    WorkCluster,
    Rating,
    Staff,
    TaggedWork,
    Trope,
    Recommendation,
    Suggestion,
    Pairing,
    Reference,
    ColdStartRating,
    WorkTitle,
    Work
)


def is_param_null(param):
    return param == 'None' or (not param) or param is None


UNK_VALUES = {'Inconnu'}


def is_empty_field(field):
    return field is None or field in UNK_VALUES


PRECOMPUTED_FIELDS = {'sum_ratings',
                      'nb_ratings',
                      'nb_likes',
                      'nb_dislikes',
                      'controversy',
                      'title_search',
                      'redirect_id'}


class ActionType(IntEnum):
    DO_NOTHING = 0
    JUST_CONFIRM = 1
    CHOICE_REQUIRED = 2


def field_changeset(works):
    rows = defaultdict(list)

    for work in works:
        for field in work:
            rows[field].append(work[field])

    for field, choices in rows.items():
        suggested = None

        if field == 'id':
            action = ActionType.JUST_CONFIRM
            suggested = min(choices)
        elif field in PRECOMPUTED_FIELDS:
            action = ActionType.DO_NOTHING
        # Equality on all values.
        elif all(choice == choices[0] for choice in choices):
            action = ActionType.JUST_CONFIRM
            suggested = choices[0]
        # All but one field empty.
        elif sum(is_empty_field(choice) for choice in choices) == len(choices) - 1:
            action = ActionType.JUST_CONFIRM
            suggested = [choice for choice in choices if not is_empty_field(choice)][0]
        else:
            action = ActionType.CHOICE_REQUIRED

        yield (field, choices, action, suggested)


class WorkClusterMergeHandler:

    def __init__(self, cluster: WorkCluster, works_to_merge, target_work):
        self.cluster = cluster
        self.works_to_merge = works_to_merge
        self.target_work = target_work

    def accept_cluster(self, checker):
        WorkCluster.objects.filter(id=self.cluster.id).update(
            checker=checker,
            resulting_work=self.target_work,
            merged_on=timezone.now(),
            status='accepted')

    def overwrite_fields(self,
                         fields_to_choose,
                         fields_required,
                         new_params):
        missing_required_fields = []

        for field in fields_to_choose:
            cur_field = new_params.get(field)

            if not is_param_null(cur_field):
                setattr(self.target_work, field, cur_field)

            if is_param_null(cur_field) and field in fields_required:
                missing_required_fields.append(field)

        if not missing_required_fields:
            self.target_work.save()

        return missing_required_fields

    def perform_redirections(self):
        self.redirect_ratings()
        self.redirect_staff()
        self.redirect_related_objects()
        self.merge_references()

    def redirect_ratings(self):
        # Get all IDs of considered ratings
        get_id_of_rating = {}
        for rating_id, user_id, date in Rating.objects.filter(work__in=self.works_to_merge).values_list('id', 'user_id',
                                                                                                        'date'):
            get_id_of_rating[(user_id, date)] = rating_id
        # What is the latest rating of every user? (N. B. – latest may be null)
        kept_rating_ids = []
        latest_ratings = (Rating.objects.filter(
            work__in=self.works_to_merge
        ).values('user_id').annotate(latest=Max('date')))
        for rating in latest_ratings:
            user_id = rating['user_id']
            date = rating['latest']
            kept_rating_ids.append(get_id_of_rating[(user_id, date)])
        Rating.objects.filter(work__in=self.works_to_merge).exclude(id__in=kept_rating_ids).delete()
        Rating.objects.filter(id__in=kept_rating_ids).update(work_id=self.target_work.id)

    def redirect_staff(self):
        target_work_staff = set()
        kept_staff_ids = []
        # Only one query: put self.target_work's Staff objects first in the list
        queryset = (Staff.objects.filter(work__in=self.works_to_merge)
            .annotate(belongs_to_target_work=Case(
                When(work_id=self.target_work.id, then=Value(1)),
                     default=Value(0), output_field=IntegerField()))
            .order_by('-belongs_to_target_work')
            .values_list('id', 'work_id', 'artist_id', 'role_id'))
        for staff_id, work_id, artist_id, role_id in queryset:
            if work_id == self.target_work.id:  # This condition will be met for the first iterations
                target_work_staff.add((artist_id, role_id))
            # Now we are sure we know every staff of the final work
            elif (artist_id, role_id) not in target_work_staff:
                kept_staff_ids.append(staff_id)
        Staff.objects.filter(work__in=self.works_to_merge).exclude(work_id=self.target_work.id).exclude(
            id__in=kept_staff_ids).delete()
        Staff.objects.filter(id__in=kept_staff_ids).update(work_id=self.target_work.id)

    def merge_references(self):
        def compute_hash(source, identifier):
            return hash(source + str(identifier))

        references = Reference.objects.filter(work__in=self.works_to_merge).all()
        kept_references = dict()
        target_work_references = {compute_hash(ref.source, ref.identifier) for ref in references
                                  if ref.work_id == self.target_work.id}

        for reference in references:
            h = compute_hash(reference.source, reference.identifier)
            if h not in target_work_references:
                kept_references[h] = reference.id

        for ref_id in kept_references:
            Reference.objects.filter(id=ref_id).update(work_id=self.target_work.id)

    def redirect_related_objects(self):
        genres = sum((list(work.genre.all()) for work in self.works_to_merge), [])
        work_ids = [work.id for work in self.works_to_merge]
        existing_tag_ids = TaggedWork.objects.filter(work=self.target_work).values_list('tag__pk', flat=True)

        self.target_work.genre.add(*genres)
        Trope.objects.filter(origin_id__in=work_ids).update(origin_id=self.target_work.id)
        TaggedWork.objects.filter(work_id__in=work_ids).exclude(tag_id__in=existing_tag_ids).update(
            work_id=self.target_work.id)
        for model in [WorkTitle, Suggestion, Recommendation, Pairing, ColdStartRating]:
            model.objects.filter(work_id__in=work_ids).update(work_id=self.target_work.id)

        Work.objects.filter(id__in=work_ids).exclude(id=self.target_work.id).update(redirect=self.target_work)


def merge_work_clusters(*clusters):
    target_cluster = clusters[0]
    for cluster in clusters[1:]:
        union_work_cluster(target_cluster, list(cluster.works.all()))
        cluster.delete()
    return target_cluster


def union_work_cluster(cluster, works):
    cluster.works.add(*works)


def create_work_cluster(works):
    # FIXME: Do an actual Union-Find.
    target_cluster = None
    for work in works:
        clusters = list(work.workcluster_set.all())
        if clusters:
            target_cluster = clusters[0]
            break

    if not target_cluster:
        target_cluster = WorkCluster.objects.create()

    union_work_cluster(target_cluster, works)

    return target_cluster
