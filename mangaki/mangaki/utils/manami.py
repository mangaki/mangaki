from typing import (Tuple, Set, Dict, DefaultDict, NewType, List, Iterator,
                    Any, Optional)
import logging
import pathlib
import json
import re
from collections import Counter, defaultdict
from urllib.parse import urlparse
from datetime import datetime
from tryalgo.kruskal import UnionFind
import pandas as pd
from django.db import DataError
from mangaki.models import Work, Reference, WorkTitle, TaggedWork, Tag


MAX_MANAMI_ENTRIES = 100000


KEPT_ANIDB_DUPLICATES = set(map(str, {
    # 5101 & 5841: Clannad
    # 7525: OreImo
    # 4897: Baccano
    # 4932: Kara no Kyoukai
    # 8778: Madoka Magica
    4897, 5101, 5841, 7525,
    9977, 6671, 6107, 9541, 6747, 6564,
    4932, 8778
}))

category_from_type = {
    'TV': 'TV',
    'Série': 'TV',
    'série': 'TV',
    'TV Series': 'TV',
    'VOD': 'TV',
    'SPECIAL': 'Special',
    'Special': 'Special',
    'MOVIE': 'Movie',
    'Movie': 'Movie',
    'Film': 'Movie',
    'film': 'Movie',
    'ONA': 'ONA',
    'Web': 'ONA',
    'OVA': 'OVA',
    'Oav': 'OVA',
    'Music Video': 'MV',
    'UNKNOWN': None,
    'Mystère': None,
    'Shonen': None,
    'Action - Aventure - Comédie': None,
    'Other': None,
    ' ': None,
    '': None
}

coarse_category = {
    'tv': 'TV',
    'special': 'Special',
    'ona': 'Special',
    'ova': 'Special',
    'movie': 'Movie',
    'mv': 'MV',
    'unknown': None,
    None: None
}


def sanitize(string):
    standard = string.lower()
    standard = re.sub(r'[’`\']', '', standard)
    standard = re.sub(r'\W', ' ', standard)  # removing non-words characters
    standard = re.sub(r'\s+', ' ', standard)  # removing spaces at middle
    standard = re.sub(r'^\s', ' ', standard)  # removing spaces at beginning
    standard = re.sub(r'\s$', ' ', standard)  # removing spaces at end
    return standard


source_of = {
    'myanimelist': 'MAL',
    'anidb': 'AniDB',
    'kitsu': 'kitsu.io',
    'anilist': 'anilist.co'
}


# On utilise 'AniDB' et 'MAL' pour coller aux sources Mangaki
def get_manami_source(url: str) -> str:
    if url == 'https://anidb.net/anime':
        return 'AniDB'
    if url == 'https://myanimelist.net/anime':
        return 'MAL'
    return urlparse(url).netloc


Ref = NewType('Ref', Tuple[str, str])


def parse_manami_source(source: str) -> Ref:
    source_name, identifier = source.rsplit('/', 1)
    try:
        return Ref((get_manami_source(source_name), identifier))
    except Exception as exception:
        logging.exception(exception)


def ref_to_url(ref: Ref) -> str:
    source, identifier = ref
    if source == 'AniDB':
        hostname = 'anidb.net'
    elif source == 'MAL':
        hostname = 'myanimelist.net'
    else:
        hostname = source
    return f'https://{hostname}/anime/{identifier}'


class AnimeOfflineDatabase:
    def __init__(self, path: str, *,
                 manami_map: Optional[Dict[int, int]] = None):
        self._path = path
        self.references: DefaultDict[Ref, List[int]] = defaultdict(list)
        self.from_title: DefaultDict[str, Set[int]] = defaultdict(set)
        self.from_synonym: DefaultDict[str, Set[int]] = defaultdict(set)
        self.manami_map = (manami_map or
                           {k: k for k in range(MAX_MANAMI_ENTRIES)})
        self.load_database()
        self.build_reverse_indexes()
        self.df = pd.DataFrame(self._raw['data'])
        self._check()

    def load_database(self):
        with open(self._path, encoding='utf-8') as f:
            self._raw: Dict[str, Any] = json.load(f)
            for entry in self._raw['data']:
                entry['nb_episodes'] = str(entry['episodes'])
                entry['subcategory'] = coarse_category[entry['type'].lower()]
                entry['year'] = (entry['animeSeason']['year']
                                 if 'year' in entry['animeSeason'] else None)
                entry['references'] = []

    def build_reverse_indexes(self):
        for local_id, entry in enumerate(self._raw['data']):
            main_manami_id = self.manami_map[local_id]
            # Parse sources
            for source in entry['sources']:
                ref = parse_manami_source(source)
                self.references[ref].append(main_manami_id)
                entry['references'].append(ref)

            # Setup title reverse search
            self.from_title[sanitize(entry['title'])].add(main_manami_id)
            for synonym in entry['synonyms']:
                self.from_synonym[sanitize(synonym)].add(main_manami_id)

    def _check(self):
        for (source, identifier), manami_entry in self.references.items():
            assert len(manami_entry) == 1, \
                f"Multiple Manami entries with reference {source}/{identifier}"

    def __getitem__(self, key: int) -> dict:
        return self._raw['data'][key]

    def __len__(self) -> int:
        return len(self._raw['data'])

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return iter(self._raw['data'])

    def print_summary(self):
        logging.info('Manami:')
        logging.info('\t%d animes (with %d unique titles)',
                     len(self), len(self.from_title))
        logging.info('\t%d unique references', len(self.references))


class MangakiDatabase:
    def __init__(self):
        self.references = defaultdict(set)
        self.from_title = defaultdict(set)
        self.from_synonym = defaultdict(set)
        self.load_database()
        self.build_reverse_indexes()
        self.missing_refs = {
            pk for pk, raw in self._raw.items() if 'sources' not in raw}
        self.df = pd.DataFrame.from_dict(self._raw, orient='index')

    def load_database(self):
        self._raw: Dict[int, Dict[str, Any]] = {
            work_dict['pk']: work_dict for work_dict in Work.objects.filter(
                category__slug='anime').values(
            'pk', 'title', 'nb_episodes', 'date', 'anime_type', 'nb_ratings',
            'anidb_aid')
        }

        self.anidb_refs = []
        for pk, work in self._raw.items():
            self.from_title[sanitize(work['title'])].add(pk)
            work['year'] = work['date'].year if work['date'] else None
            work['nb_episodes'] = work['nb_episodes'].split('x')[0]
            category = category_from_type[work['anime_type']]
            work['subcategory'] = (coarse_category[category.lower()]
                                   if category else None)
            work['sources'] = []
            work['references'] = []
            work['synonyms'] = []
            if work['anidb_aid'] > 0:
                self.anidb_refs.append((pk, 'AniDB', str(work['anidb_aid'])))

    def build_reverse_indexes(self):
        """
        This is a complicated problem because:
        1) already merged works redirect to other works
        2) some references are linked to others (through union-find)
        3) AniDB refs are in anidb_aid attribute (they may not exist as ref)
        4) we accept having duplicate references (eg. AniDB Madoka Magica I II)
        but then we ignore the duplicates, hence the remember_anidb dict
        """
        # Redirecting already merged works because of 1)
        redirects = dict(Work.all_objects.filter(
            redirect__isnull=False).values_list('pk', 'redirect_id'))

        reference_triplets = set(list(
            Reference.objects.filter(work__category__slug='anime').values_list(
                'work_id', 'source', 'identifier')
        ) + self.anidb_refs)  # Extra refs because of 3)

        remember_anidb = {}
        for mangaki_id, source, identifier in sorted(reference_triplets):
            ref = (source, identifier)

            while mangaki_id in redirects:
                mangaki_id = redirects[mangaki_id]

            if source == 'AniDB':
                if (identifier in remember_anidb and
                        identifier in KEPT_ANIDB_DUPLICATES):  # Because of 4)
                    continue  # Skip this AniDB ref because another work has it
                remember_anidb[identifier] = mangaki_id
            self._raw[mangaki_id]['sources'].append(ref)
            self._raw[mangaki_id]['references'].append(ref)
            self.references[(source, identifier)].add(mangaki_id)

        for mangaki_id, synonym in WorkTitle.objects.values_list(
                'work_id', 'title'):
            while mangaki_id in redirects:
                mangaki_id = redirects[mangaki_id]
            if mangaki_id not in self._raw:
                continue

            self._raw[mangaki_id]['synonyms'].append(synonym)
            self.from_synonym[sanitize(synonym)].add(mangaki_id)

    def __getitem__(self, key: int) -> dict:
        return self._raw[key]

    def __len__(self) -> int:
        return len(self._raw)

    def print_summary(self):
        logging.info('Mangaki:')
        logging.info('\t%d animes', len(self))
        logging.info('\t%d unique references', len(self.references))
        if self.missing_refs:
            logging.info('\t%d animes without ref', len(self.missing_refs))


def get_clusters_from_ref(manami: AnimeOfflineDatabase,
                          dead: Dict[str, Set[str]],
                          manami_cluster_backup=[]) -> Dict[int, List[Ref]]:
    '''
    manami_cluster_backup is read-only, so we can use a mutable default.
    '''
    references: Set[Ref] = set()
    url1: DefaultDict[int, List[Ref]] = defaultdict(list)  # Manami refs
    url2: DefaultDict[int, Set[Ref]] = defaultdict(set)  # Mangaki refs

    # Get all sources of Manami entries
    for manami_id, entry in enumerate(manami):
        references.add(Ref(('Manami', str(manami_id))))
        for ref in entry['references']:
            assert check_ref(dead, ref), f'{ref} does not exist anymore'
            references.add(ref)
            url1[manami_id].append(ref)

    # Manami extra refs
    for manami_cluster in manami_cluster_backup:
        for url_cluster in manami_cluster:
            for url in url_cluster:
                ref = parse_manami_source(url)
                references.add(ref)

    # Mangaki works with AniDB ID
    anidb_id = dict(Work.objects.filter(
        anidb_aid__gt=0).values_list('id', 'anidb_aid'))
    for mangaki_id, aid in anidb_id.items():
        if str(aid) not in dead['AniDB']:
            ref1 = Ref(('Mangaki', str(mangaki_id)))
            ref2 = Ref(('AniDB', str(aid)))
            references.update([ref1, ref2])
            url2[mangaki_id].update([ref1, ref2])

    # All Mangaki references
    for mangaki_id, source, identifier in Reference.objects.filter(
            work_id__category__slug='anime').values_list(
            'work_id', 'source', 'identifier'):
        ref1 = Ref(('Mangaki', str(mangaki_id)))
        ref2 = Ref((source, identifier))
        if check_ref(dead, ref2):
            references.update([ref1, ref2])
            url2[mangaki_id].update([ref1, ref2])

    ids: Dict[Ref, int] = {v: k for k, v in enumerate(sorted(references))}
    uf = UnionFind(len(references))
    for manami_id, refs in url1.items():
        for ref in refs:
            uf.union(ids[ref], ids[Ref(('Manami', str(manami_id)))])

    # Manami duplicates
    for manami_cluster in manami_cluster_backup:
        first_ref = None
        for url_cluster in manami_cluster:
            for url in url_cluster:
                ref = parse_manami_source(url)
                if first_ref is None:
                    first_ref = ref
                else:
                    uf.union(ids[first_ref], ids[ref])

    nb_has_anidb = 0
    for mangaki_id, mangaki_refs in url2.items():
        has_anidb = False
        for ref in mangaki_refs:
            if ref[0] == 'AniDB':
                has_anidb = True
            uf.union(ids[ref], ids[Ref(('Mangaki', str(mangaki_id)))])
        nb_has_anidb += has_anidb
    if url2:
        logging.info('%d/%d ont un ID AniDB (%.1f %%)',
                     nb_has_anidb, len(url2), nb_has_anidb / len(url2) * 100)

    clusters = defaultdict(list)
    for ref, ref_id in ids.items():
        clusters[uf.find(ref_id)].append(ref)

    return clusters


def load_dead_entries(manami_path: pathlib.Path) -> Dict[str, Set[str]]:
    dead = {}
    for filename in manami_path.glob('*.json'):
        with open(filename, encoding='utf-8') as f:
            dead[source_of[filename.stem]] = set(json.load(f)['deadEntries'])
    return dead


def check_ref(dead: Dict[str, Set[str]], ref: Ref) -> bool:
    source, identifier = ref
    return source not in dead or identifier not in dead[source]


def describe_refs(manami: AnimeOfflineDatabase, mangaki_db: MangakiDatabase,
                  cluster: List[Ref],
                  valid_mangaki_ids: Set[int]) -> Tuple[list, list, List[Ref]]:
    '''
    Takes a cluster of works that refer to a unique work, and provides in a
    human-readable way the corresponding IDs in Mangaki, Manami and elsewhere.
    '''
    mangaki_refs = []
    manami_refs = []
    other_refs = []
    for source, identifier in cluster:
        if source == 'Mangaki' and int(identifier) in valid_mangaki_ids:
            mangaki_refs.append(
                (identifier, mangaki_db[int(identifier)]['title']))
        elif (source == 'Manami' and
                int(identifier) in manami.manami_map.values()):
            manami_refs.append((identifier, manami[int(identifier)]['title']))
        elif source not in {'Mangaki', 'Manami'}:
            other_refs.append(Ref((source, identifier)))
    return mangaki_refs, manami_refs, other_refs


def get_top2_source_count(dead: Dict[str, Set[str]],
                          refs: List[Ref]) -> Tuple[Counter, tuple]:
    c = Counter([ref[0] for ref in refs if check_ref(dead, ref)])
    return c, tuple(value for _, value in c.most_common(2))


def describe_clusters(manami: AnimeOfflineDatabase,
        mangaki_db: MangakiDatabase, dead: Dict[str, Set[str]],
        clusters: Dict[int, List[Ref]]) -> Tuple[Counter, int, int, int, dict]:
    '''
    Each cluster contains a certain number of Mangaki IDs or Manami IDs.
    For example (3, 4) means this cluster refers to 3 different works in
    Mangaki and 4 different works in Manami.
    For example, all Madoka Magica movies may have the same reference to AniDB.
    What we are mainly interested in is (0, 1): new works from Manami.
    Returns a Counter of those cluster types, and new works from Manami to add.
    '''
    works = Work.objects.in_bulk()
    c: Counter = Counter()
    clusters_by_occ = defaultdict(list)
    nb_cdup_mangaki = 0
    nb_cdup_manami = 0
    total_ref = 0
    search_queries = []
    mangaki_not_manami = set()
    manami_clusters = {}
    mangaki_clusters = []
    to_create = []
    valid_mangaki_ids = set(Work.objects.filter(
        category__slug='anime').values_list('id', flat=True))
    for cluster in clusters.values():
        mangaki_refs, manami_refs, other_refs = describe_refs(
            manami, mangaki_db, cluster, valid_mangaki_ids)
        nb_mangaki = len(mangaki_refs)
        nb_manami = len(manami_refs)

        # (6, 7): Kara no Kyoukai
        # (3, 4): Puella Magi Madoka Magica
        # (2, 2): (like these, see KEPT_ANIDB_DUPLICATES in manami.py)

        if nb_mangaki > 0:
            total_ref += len(cluster) - nb_mangaki - nb_manami
        if nb_mangaki >= 2 and nb_manami >= 1:
            nb_cdup_mangaki += 1
        if nb_manami >= 2 and nb_mangaki >= 1:
            nb_cdup_manami += 1

        if nb_mangaki == 1:
            for source, identifier in other_refs:
                to_create.append(Reference(
                    work_id=mangaki_refs[0][0], source=source,
                    identifier=identifier))

        if nb_mangaki == 1 and nb_manami in {2, 3}:
            refcounter, _ = get_top2_source_count(dead, cluster)
            nb_ratings = sum(works[int(mangaki_id)].nb_ratings
                             for mangaki_id, _ in mangaki_refs)
            if nb_ratings > 0:
                logging.warning('%d %s %s %d', nb_ratings, mangaki_refs,
                                manami_refs, len(cluster))
                logging.critical(refcounter)

            mangaki_clusters.append(
                {int(mangaki_id) for mangaki_id, _ in mangaki_refs})

        if nb_mangaki >= 3 or nb_manami >= 3:  # Have to analyze
            clusters_by_occ[nb_mangaki, nb_manami].append(cluster)
        if nb_mangaki == 0 and nb_manami == 1:  # In Manami but not in Mangaki
            manami_ids = [int(manami_id) for manami_id, _ in manami_refs]
            manami_main_id = manami.manami_map[manami_ids[0]]
            search_queries.append(manami[manami_main_id]['title'])
            manami_clusters[manami_main_id] = manami_ids
        if nb_manami == 0:
            for identifier in mangaki_refs:
                mangaki_not_manami.add(identifier)
        c[nb_mangaki, nb_manami] += 1
    return c, nb_cdup_mangaki, nb_cdup_manami, total_ref, manami_clusters


def get_manami_map_from_backup(manami,
                               manami_cluster_backup: list) -> Dict[int, int]:
    '''
    A cluster backup should be a list of list of list of references.
    For each i, manami_cluster_backup[i] represents references lists that refer
    to the same work. This can be used to make the manami_map.
    '''
    manami_map = manami.manami_map
    cluster_length_counter: Counter = Counter()
    for manami_cluster in manami_cluster_backup:
        manami_ids = list()
        for url_cluster in manami_cluster:
            for url in url_cluster:
                ref = parse_manami_source(url)
                if ref in manami.references:
                    manami_ids.append(min(manami.references[ref]))
        manami_ids = list(set(sorted(manami_ids)))
        for manami_id in manami_ids[1:]:
            manami_map[manami_id] = manami_ids[0]  # Smallest = repr of cluster
        cluster_length_counter[len(manami_ids)] += 1
    return manami_map


def drop_dup(column: pd.Series) -> list:
    '''
    Aggregation function for pandas.
    Takes a pandas column which is a list of lists (e.g. of synonyms)
    Concatenates everything (sum) removes duplicates (set) and returns a list.
    '''
    return list(set(sum(column.tolist(), start=[])))


def keep_most_common(column: pd.Series) -> str:
    '''
    Aggregation function for pandas.
    Takes a pandas column which is a list of attributes (e.g. years)
    Keeps the most common one.
    '''
    return Counter(column.astype(str).tolist()).most_common()[0][0]


def insert_combined_manami_to_mangaki(to_create: DefaultDict[str, list],
                                      entry: Dict[str, Any]):
    # Parse references
    anidb_aid = None
    refs = []
    for source, identifier in entry['references']:
        if source == 'AniDB':
            anidb_aid = identifier
        refs.append(Reference(source=source, identifier=identifier,
                              url=ref_to_url(Ref((source, identifier)))))

    date = None
    try:
        date = datetime(int(float(entry['year'])), 1, 1)
    except ValueError:
        pass
    # Create work
    work, _ = Work.objects.get_or_create(
        title=entry['title'],
        category_id=1,
        anime_type=entry['type'],
        ext_poster=entry['picture'],
        nb_episodes=entry['episodes'],
        date=date,
        anidb_aid=anidb_aid if anidb_aid is not None else 0,
    )

    # Save references
    for ref in refs:
        ref.work_id = work.id
    to_create['refs'].extend(refs)

    # Create synonyms; tags is boring because of the forced AniDB ID
    for synonym in entry['synonyms']:
        to_create['synonyms'].append(WorkTitle(
            work_id=work.id, title=synonym, type='synonym'))

    # Create available tags
    for tag in Tag.objects.filter(title__in=entry['tags']):
        to_create['tags'].append(TaggedWork(work=work, tag=tag))


def insert_into_mangaki(manami: AnimeOfflineDatabase,
                        manami_clusters: Dict[int, List[int]]):
    to_create: DefaultDict[str, list] = defaultdict(list)
    combiner = {
        field: drop_dup if field in {'sources', 'synonyms', 'relations',
                                     'tags', 'references'}
        else keep_most_common for field in manami.df.columns
    }
    for _, manami_cluster in manami_clusters.items():
        combined = manami.df.loc[list(manami_cluster)].groupby(
            lambda _: True).agg(combiner).loc[True]
        try:
            insert_combined_manami_to_mangaki(to_create, combined)
        except DataError as exception:
            logging.exception(exception)
            break

    Reference.objects.bulk_create(to_create['refs'], ignore_conflicts=True)
    WorkTitle.objects.bulk_create(to_create['synonyms'], ignore_conflicts=True)
    TaggedWork.objects.bulk_create(to_create['tags'], ignore_conflicts=True)
