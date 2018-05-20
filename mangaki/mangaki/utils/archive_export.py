import os

import csv
import inspect
import tempfile
from contextlib import contextmanager
from django.contrib.auth.models import User
from zipfile import ZipFile

from mangaki.models import (
    Rating,
    Suggestion,
    Evidence,
    WorkCluster,
    Neighborship,
    SearchIssue,
    Recommendation,
    Pairing,
    ColdStartRating,
    UserBackgroundTask,
    UserArchive
)


def export_workclusters(user: User, writer):
    work_clusters = WorkCluster.objects.filter(user=user).prefetch_related('works__title',
                                                                           'checker__username',
                                                                           'resulting_work__title')

    writer.writerow(['reported_on', 'status', 'checker', 'resulting_work', 'merged_on', 'origin', 'works'])
    for wc in work_clusters.iterator():
        writer.writerow([
            wc.reported_on,
            wc.status,
            wc.checker.username if wc.checker else '',
            wc.resulting_work.title if wc.resulting_work else '',
            wc.merged_on,
            wc.origin,
            '|'.join([work.title for work in wc.works.iterator()])
        ])


def export_archive_records(user: User, writer):
    writer.writerow(['updated_on', 'local_archive_path'])
    for archive in UserArchive.objects.filter(owner=user).iterator():
        try:
            writer.writerow([archive.updated_on, archive.local_archive.path])
        except ValueError:
            writer.writerow([archive.updated_on, ''])


target_models = {
    Rating: ['work__title', 'date', 'choice'],
    Suggestion: ['id', 'work__title', 'date', 'problem', 'message', 'is_checked'],
    Evidence: ['suggestion', 'agrees', 'needs_help'],
    WorkCluster: export_workclusters,
    Neighborship: ['neighbor__username', 'score'],
    SearchIssue: ['date', 'title', 'poster', 'mal_id', 'score'],
    Recommendation: ['target_user__username', 'work__title'],
    Pairing: ['date', 'artist__name', 'work__title', 'is_checked'],
    ColdStartRating: ['work__title', 'choice', 'date'],
    UserBackgroundTask: ['created_on', 'task_id', 'tag'],
    UserArchive: export_archive_records
}

models_user_keys = {
    UserBackgroundTask: 'owner'
}

target_filenames = {
    Rating: 'ratings.csv',
    Suggestion: 'suggestions.csv',
    Evidence: 'evidences.csv',
    WorkCluster: 'work_clusters.csv',
    Neighborship: 'neighborships.csv',
    SearchIssue: 'search_issues.csv',
    Recommendation: 'recommendations.csv',
    Pairing: 'pairings.csv',
    ColdStartRating: 'cold_start_ratings.csv',
    UserBackgroundTask: 'user_background_tasks.csv',
    UserArchive: 'user_archives.csv'
}


class UserDataArchiveBuilder:

    def __init__(self, user: User):
        self.user = user

        self.temp_dir = tempfile.TemporaryDirectory(prefix='user_exports')
        self.archive = ZipFile(
            os.path.join(self.temp_dir.name, 'data.zip'),
            'w'
        )

    @property
    def archive_filename(self):
        return os.path.join(self.temp_dir.name, 'data.zip')

    def cleanup(self):
        self.temp_dir.cleanup()

    @contextmanager
    def create_file_in_archive(self, filename: str):
        file_path = os.path.join(self.temp_dir.name, filename)
        f = open(file_path, 'w')
        yield f
        f.close()
        self.archive.write(file_path, filename)
        os.remove(file_path)


def export_generic(model, fields):
    prefetch_fields = [field for field in fields if '__' in field]
    user_key = models_user_keys.get(model, 'user')

    def perform_writes(user: User, writer):
        qs = model.objects.filter(**{user_key: user}).prefetch_related(*prefetch_fields).values_list(*fields)

        writer.writerow(fields)
        for item in qs.iterator():
            writer.writerow(list(map(str, item)))

    perform_writes.name = 'export_{}'.format(str(model))
    return perform_writes


def export(archive: UserDataArchiveBuilder):
    for model, fields_or_exporter in target_models.items():
        # FIXME: evaluate if a model is empty or not before opening its file.
        with archive.create_file_in_archive(target_filenames[model]) as file:
            writer = csv.writer(file)
            if inspect.isfunction(fields_or_exporter):
                fields_or_exporter(archive.user, writer)
            else:
                export_generic(model,
                               fields_or_exporter)(archive.user, writer)
