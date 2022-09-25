# SPDX-FileCopyrightText: 2022, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from pathlib import Path
import json
import logging
from django.core.management.base import BaseCommand
from mangaki.utils.manami import (
    AnimeOfflineDatabase, MangakiDatabase, load_dead_entries,
    get_clusters_from_ref, describe_clusters, get_manami_map_from_backup,
    insert_into_mangaki)


class Command(BaseCommand):
    args = ''
    help = 'Add new works from Manami'

    def add_arguments(self, parser):
        parser.add_argument('manami_path', type=str,
            help="Path to manami-project's anime-offline-database repo")
        parser.add_argument('--extra-clusters', type=str,
            help='Path to optional list of lists of URL lists that refer to '
                 'the same work')
        parser.add_argument('--dry-run', action='store_true', default=False,
            help='If true, then it will not modify the database')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        extra_clusters_filename = options.get('extra_clusters')
        manami_cluster_backup = []
        if extra_clusters_filename is not None:
            with open(extra_clusters_filename, encoding='utf-8') as f:
                manami_cluster_backup = json.load(f)

        manami_path = Path(options.get('manami_path'))
        dead = load_dead_entries(manami_path / 'dead-entries')

        manami = AnimeOfflineDatabase(
            manami_path / 'anime-offline-database.json')
        if manami_cluster_backup:
            manami_map = get_manami_map_from_backup(manami,
                                                    manami_cluster_backup)
            manami = AnimeOfflineDatabase(
                manami_path / 'anime-offline-database.json',
                manami_map=manami_map)
        manami.print_summary()

        mangaki_db = MangakiDatabase()
        mangaki_db.print_summary()

        clusters = get_clusters_from_ref(manami, dead, manami_cluster_backup)
        c, nb_cdup_mangaki, nb_cdup_manami, total_ref, manami_clusters = (
            describe_clusters(manami, mangaki_db, dead, clusters))

        logging.warning('nb mangaki / nb manami: %s', c)
        if not dry_run:
            # Insert into Mangaki those manami_clusters
            insert_into_mangaki(manami, manami_clusters)
