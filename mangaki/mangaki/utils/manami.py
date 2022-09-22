from typing import Tuple
import logging
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


def sanitize(s):
    standard = s.lower()
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


Ref = Tuple[str]


def parse_manami_source(source: str) -> Ref:
    source_name, identifier = source.rsplit('/', 1)
    try:
        return get_manami_source(source_name), identifier
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
    def __init__(self, path: str, *, manami_map=None):
        self._path = path
        self.references = defaultdict(list)
        self.from_title = defaultdict(set)
        self.from_synonym = defaultdict(set)
        self.manami_map = (manami_map or
                           {k: k for k in range(MAX_MANAMI_ENTRIES)})

        with open(self._path, encoding='utf-8') as f:
            self._raw = json.load(f)
            for entry in self._raw['data']:
                entry['nb_episodes'] = str(entry['episodes'])
                entry['subcategory'] = coarse_category[entry['type'].lower()]
                entry['year'] = (entry['animeSeason']['year']
                                 if 'year' in entry['animeSeason'] else None)

        for local_id, datum in enumerate(self._raw['data']):
            main_manami_id = self.manami_map[local_id]
            # Parse sources
            for source in datum['sources']:
                source, identifier = parse_manami_source(source)
                self.references[(source, identifier)].append(main_manami_id)
                datum.setdefault('references', []).append((source, identifier))

            # Setup title reverse search
            self.from_title[sanitize(datum['title'])].add(main_manami_id)
            for synonym in datum['synonyms']:
                self.from_synonym[sanitize(synonym)].add(main_manami_id)

        self.df = pd.DataFrame(self._raw['data'])
        self._check()

    def _check(self):
        for (source, identifier), manami_entry in self.references.items():
            assert (
                len(manami_entry) == 1,
                f"Multiple Manami entries with reference {source}/{identifier}"
            )

    def __getitem__(self, key):
        return self._raw['data'][key]

    def __len__(self):
        return len(self._raw['data'])

    def print_summary(self):
        logging.info('Manami:')
        logging.info('\t%d animes (with %d unique titles)',
                     len(self), len(self.from_title))
        logging.info(f'\t%d unique references', len(self.references))


class MangakiDatabase:
    def __init__(self):
        self._raw = {work['pk']: work for work in Work.objects.filter(
            category__slug='anime').values(
            'pk', 'title', 'nb_episodes', 'date', 'anime_type', 'nb_ratings')}
        self.references = defaultdict(set)
        self.from_title = defaultdict(set)
        self.from_synonym = defaultdict(set)

        # Extract all Mangaki references
        redirects = dict(Work.all_objects.filter(
            redirect__isnull=False).values_list('pk', 'redirect_id'))

        remember_anidb = {}
        """
        We use `Reference.objects` so that we also get duplicated works.
        References on duplicated works should have been moved to the cluster
        representative, but it doesn't hurt to be conservative.
        """
        qs = Reference.objects.filter(work_id__in=Work.objects.all(),
                                      work_id__category__slug='anime') \
                              .values_list('work_id', 'source', 'identifier')

        extra_ref = []
        for mangaki_id, anidb_id in Work.objects.filter(
                anidb_aid__gt=0).values_list('id', 'anidb_aid'):
            extra_ref.append((mangaki_id, 'AniDB', str(anidb_id)))
        qs = set(list(qs) + extra_ref)

        for mangaki_id, source, identifier in sorted(qs):
            ref = (source, identifier)
            # Clean up known duplicates.  NB: These are bogus DB entries.
            while mangaki_id in redirects:
                mangaki_id = redirects[mangaki_id]

            if source == 'AniDB':
                """
                OK this is subtle. We usually do not allow duplicate refs,
                except for AniDB (e.g. Madoka Magica I, II, III). In this case,
                the first anime keeps the AniDB ref in this MangakiDatabase
                object, the other ones not (to avoid unnecessary merges).
                It works fine in 99% of cases.
                """
                if (identifier in remember_anidb and
                        identifier in KEPT_ANIDB_DUPLICATES):
                    self._raw[mangaki_id].setdefault('sources', [])
                    self._raw[mangaki_id].setdefault('references', [])
                    continue
                remember_anidb[identifier] = mangaki_id
            self._raw[mangaki_id].setdefault('sources', []).append(ref)
            self._raw[mangaki_id].setdefault('references', []).append(ref)
            self.references[(source, identifier)].add(mangaki_id)

        self.missing_refs = {
            pk for pk, raw in self._raw.items() if 'sources' not in raw}

        for pk, work in self._raw.items():
            self.from_title[sanitize(work['title'])].add(pk)
            work['year'] = work['date'].year if work['date'] else None
            work['nb_episodes'] = work['nb_episodes'].split('x')[0]
            category = category_from_type[work['anime_type']]
            work['subcategory'] = (coarse_category[category.lower()]
                                   if category else None)

        for work_id, synonym in WorkTitle.objects.values_list(
                'work_id', 'title'):
            while work_id in redirects:
                work_id = redirects[work_id]
            if work_id not in self._raw:
                continue

            self._raw[work_id].setdefault('synonyms', []).append(synonym)
            self.from_synonym[sanitize(synonym)].add(work_id)

        self.df = pd.DataFrame.from_dict(self._raw, orient='index')

    def __getitem__(self, key):
        return self._raw[key]

    def __len__(self):
        return len(self._raw)

    def print_summary(self):
        logging.info('Mangaki:')
        logging.info('\t%d animes', len(self))
        logging.info('\t%d unique references', len(self.references))
        if self.missing_refs:
            logging.info('\t%d animes without ref', len(self.missing_refs))


def get_clusters_from_ref(manami, dead, manami_cluster_backup=[]):
    references = set()
    url1 = defaultdict(list)  # Refs on Manami side
    url2 = defaultdict(set)  # Refs on Mangaki side

    # Get all sources of Manami entries
    for manami_id, entry in enumerate(manami):
        references.add(('Manami', str(manami_id)))
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
            ref1 = ('Mangaki', str(mangaki_id))
            ref2 = ('AniDB', str(aid))
            references.update([ref1, ref2])
            url2[mangaki_id].update([ref1, ref2])

    # All Mangaki references
    for mangaki_id, source, identifier in Reference.objects.filter(
            work_id__category__slug='anime').values_list(
            'work_id', 'source', 'identifier'):
        ref1 = ('Mangaki', str(mangaki_id))
        ref2 = (source, identifier)
        if check_ref(dead, ref2):
            references.update([ref1, ref2])
            url2[mangaki_id].update([ref1, ref2])

    ids = dict(zip(sorted(references), range(len(references))))
    uf = UnionFind(len(references))
    for manami_id, refs in url1.items():
        for ref in refs:
            uf.union(ids[ref], ids['Manami', str(manami_id)])

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
    for mangaki_id, refs in url2.items():
        has_anidb = False
        for ref in refs:
            if ref[0] == 'AniDB':
                has_anidb = True
            uf.union(ids[ref], ids['Mangaki', str(mangaki_id)])
        nb_has_anidb += has_anidb
    logging.info('%d/%d ont un ID AniDB (%.1f %%)',
                 nb_has_anidb, len(url2), nb_has_anidb / len(url2) * 100)

    clusters = defaultdict(list)
    for ref, ref_id in ids.items():
        clusters[uf.find(ref_id)].append(ref)

    return clusters


def load_dead_entries(manami_path):
    dead = {}
    for filename in manami_path.glob('*.json'):
        with open(filename, encoding='utf-8') as f:
            dead[source_of[filename.stem]] = set(json.load(f)['deadEntries'])
    return dead


def check_ref(dead: dict, ref: Ref) -> bool:
    source, identifier = ref
    return source not in dead or identifier not in dead[source]


def describe_refs(manami, mangaki_db, cluster, valid_mangaki_ids):
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
            other_refs.append((source, identifier))
    return mangaki_refs, manami_refs, other_refs


def get_top2_source_count(dead, refs):
    c = Counter([ref[0] for ref in refs if check_ref(dead, ref)])
    return c, tuple(value for _, value in c.most_common(2))


def describe_clusters(manami, mangaki_db, dead, clusters):
    '''
    Each cluster contains a certain number of Mangaki IDs or Manami IDs.
    For example (3, 4) means this cluster refers to 3 different works in
    Mangaki and 4 different works in Manami.
    For example, all Madoka Magica movies may have the same reference to AniDB.
    What we are mainly interested in is (0, 1): new works from Manami.
    '''
    works = Work.objects.in_bulk()
    c = Counter()
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


def get_manami_map_from_backup(manami, manami_cluster_backup):
    '''
    A cluster backup should be a list of list of list of references.
    For each i, manami_cluster_backup[i] represents references lists that refer
    to the same work. This can be used to make the manami_map.
    '''
    manami_map = manami.manami_map
    cluster_length_counter = Counter()
    for manami_cluster in manami_cluster_backup:
        manami_ids = set()
        for url_cluster in manami_cluster:
            for url in url_cluster:
                ref = parse_manami_source(url)
                if ref in manami.references:
                    manami_ids.add(min(manami.references[ref]))
        manami_ids = list(sorted(manami_ids))
        for manami_id in manami_ids[1:]:
            manami_map[manami_id] = manami_ids[0]  # Smallest = repr of cluster
        cluster_length_counter[len(manami_ids)] += 1
    return manami_map


def drop_dup(column) -> list:
    '''
    Aggregation function for pandas.
    Takes a pandas column which is a list of lists (e.g. of synonyms)
    Concatenates everything (sum) removes duplicates (set) and returns a list.
    '''
    return list(set(sum(column.tolist(), start=[])))


def keep_most_common(column) -> str:
    '''
    Aggregation function for pandas.
    Takes a pandas column which is a list of attributes (e.g. years)
    Keeps the most common one.
    '''
    return Counter(column.astype(str).tolist()).most_common()[0][0]


def insert_combined_manami_to_mangaki(to_create, entry):
    # Parse references
    anidb_aid = None
    refs = []
    for source, identifier in entry['references']:
        if source == 'AniDB':
            anidb_aid = identifier
        refs.append(Reference(source=source, identifier=identifier,
                              url=ref_to_url((source, identifier))))

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


def insert_into_mangaki(manami, manami_clusters):
    to_create = defaultdict(list)
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
