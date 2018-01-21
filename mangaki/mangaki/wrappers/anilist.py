from datetime import datetime
from enum import Enum
from collections import namedtuple
from typing import Dict, List, Tuple, Optional, Any, Generator
from urllib.parse import urljoin
import time
import os

import requests
from django.utils.functional import cached_property
from django.db.models import Q

from mangaki import settings
from mangaki.models import (Work, RelatedWork, WorkTitle, Reference, Category,
                            ExtLanguage, Studio, Genre, Artist, Staff, Role)


# Filenames for AniList GraphQL queries
ANILIST_QUERIES = {
    'user-list': 'user-list',
    'seasonal-animes': 'seasonal-animes',
    'work-info': 'work-info'
}


def read_graphql_query(filename):
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'anilist-graphql-queries', filename+'.graphql')
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def fuzzydate_to_python_datetime(date):
    """
    Converts AniList's fuzzydate to Python datetime format.
    >>> fuzzydate_to_python_datetime({'year': 2015, 'month': 7, 'day': 14})
    datetime.datetime(2015, 7, 14, 0, 0)
    >>> fuzzydate_to_python_datetime({'year': 2015, 'month': 7, 'day': None})
    datetime.datetime(2015, 7, 1, 0, 0)
    >>> fuzzydate_to_python_datetime({'year': 2015, 'month': None, 'day': None})
    datetime.datetime(2015, 1, 1, 0, 0)
    >>> fuzzydate_to_python_datetime({'year': None, 'month': None, 'day': 14})
    None
    >>> fuzzydate_to_python_datetime({'year': None, 'month': 7, 'day': None})
    None
    >>> fuzzydate_to_python_datetime({'year': None, 'month': None, 'day': None})
    None
    """

    if (date['year'] is None):
        return None
    if (date['year'] is None) and (date['month'] is None) and (date['day'] is not None):
        return None
    return datetime(date['year'], date['month'] or 1, date['day'] or 1)

def to_anime_season(date):
    """
    Return the season corresponding to a date
    >>> to_anime_season(datetime.datetime(2017, 3, 3, 0, 0))
    'AniListSeason.SPRING'
    """

    if date.month in (12, 1, 2):
        return AniListSeason.WINTER
    elif date.month in (3, 4, 5):
        return AniListSeason.SPRING
    elif date.month in (6, 7, 8):
        return AniListSeason.SUMMER
    elif date.month in (9, 10, 11):
        return AniListSeason.FALL
    return AniListSeason.UNKNOWN


class AniListException(Exception):
    """
    This class defines a custom Exception for errors with the AniList's API
    """

    def __init__(self, errors):
        super().__init__()
        self.errors = errors

    def __str__(self):
        return '\n'.join(map(lambda error: 'Error {} : {}'.format(error['status'], error['message']), self.errors))


class AniListLanguages:
    @cached_property
    def romaji_ext_lang(self) -> ExtLanguage:
        return ExtLanguage.objects.select_related('lang').get(source='anilist', ext_lang='romaji')

    @cached_property
    def english_ext_lang(self) -> ExtLanguage:
        return ExtLanguage.objects.select_related('lang').get(source='anilist', ext_lang='english')

    @cached_property
    def japanese_ext_lang(self) -> ExtLanguage:
        return ExtLanguage.objects.select_related('lang').get(source='anilist', ext_lang='japanese')

    @cached_property
    def unknown_ext_lang(self) -> ExtLanguage:
        return ExtLanguage.objects.select_related('lang').get(source='anilist', ext_lang='unknown')


class WorkCategories:
    @cached_property
    def anime(self) -> Category:
        return Category.objects.get(slug=AniListWorkType.ANIME.value)

    @cached_property
    def manga(self) -> Category:
        return Category.objects.get(slug=AniListWorkType.MANGA.value)


class StaffRoles:
    @cached_property
    def role_map(self) -> Dict[str, Role]:
        return {role.slug: role for role in Role.objects.all()}


class AniListWorkType(Enum):
    """
    This class enumerates the different kinds of works found on AniList
    """

    ANIME = 'anime'
    MANGA = 'manga'


class AniListSeason(Enum):
    """
    This class enumerates the different seasons on AniList
    """

    WINTER = 'Months December to February'
    SPRING = 'Months March to May'
    SUMMER = 'Months June to August'
    FALL = 'Months September to November'
    UNKNOWN = 'Unknown season'


class AniListStatus(Enum):
    """
    This class enumerates the different kinds of airing (or publising) statuses
    for animes (or mangas) on AniList
    """

    FINISHED = 'Has completed and is no longer being released'
    RELEASING = 'Currently releasing'
    NOT_YET_RELEASED = 'To be released at a later date'
    CANCELLED = 'Ended before the work could be finished'


class AniListRelationType(Enum):
    """
    This class enumerates the different kinds of relations between works found
    on AniList
    """

    ADAPTATION = 'An adaption of the media into a different format'
    PREQUEL = 'Released before the relation'
    SEQUEL = 'Released after the relation'
    PARENT = 'The media a side story is from'
    SIDE_STORY = 'A side story of the parent media'
    CHARACTER = 'Shares at least 1 character'
    SUMMARY = 'Shares at least 1 character'
    ALTERNATIVE = 'An alternative version of the same media'
    SPIN_OFF = 'An alternative version of the media with a different primary focus'
    OTHER = 'Other'


class AniListMediaFormat(Enum):
    """
    This class enumerates the different media formats found on AniList
    """

    TV = 'Anime broadcast on television'
    TV_SHORT = 'Anime which are under 15 minutes in length and broadcast on television'
    MOVIE = 'Anime movies with a theatrical release'
    SPECIAL = 'Special episodes that have been included in DVD/Blu-ray releases, picture dramas, pilots, etc'
    OVA = '(Original Video Animation) Anime that have been released directly on DVD/Blu-ray without originally going through a theatrical release or television broadcast'
    ONA = '(Original Net Animation) Anime that have been originally released online or are only available through streaming services.'
    MUSIC = 'Short anime released as a music video'
    MANGA = 'Professionally published manga with more than one chapter'
    NOVEL = 'Written books released as a novel or series of light novels'
    ONE_SHOT = 'Manga with just one chapter'


AniListUserEntry = namedtuple('AniListUserEntry', ('work', 'score'))
AniListStaff = namedtuple('AniListStaff', ('id', 'name_first', 'name_last', 'role'))
AniListRelation = namedtuple('AniListRelation', ('related_id', 'relation_type'))


class AniListEntry:
    """
    This class stores informations for AniList entries given a JSON.
    """

    def __init__(self, work_info, work_type: AniListWorkType):
        self.work_info = work_info
        self.work_type = work_type

        if self.work_info['type'] != work_type.name:
            raise ValueError('AniList data not from {}'.format(work_type.value))

    @property
    def anilist_id(self) -> int:
        return self.work_info['id']

    @property
    def anilist_url(self) -> int:
        return self.work_info['siteUrl']

    @property
    def media_format(self) -> AniListMediaFormat:
        return AniListMediaFormat[self.work_info['format']]

    @property
    def title(self) -> str:
        return self.work_info['title']['romaji']

    @property
    def english_title(self) -> str:
        return self.work_info['title']['english']

    @property
    def japanese_title(self) -> str:
        return self.work_info['title']['native']

    @property
    def synonyms(self) -> List[str]:
        return list(filter(None, self.work_info['synonyms']))

    @property
    def start_date(self) -> Optional[datetime]:
        return fuzzydate_to_python_datetime(self.work_info['startDate'])

    @property
    def end_date(self) -> Optional[datetime]:
        return fuzzydate_to_python_datetime(self.work_info['endDate'])

    @property
    def season(self) -> AniListSeason:
        return AniListSeason[self.work_info['season']]

    @property
    def description(self) -> str:
        return self.work_info['description']

    @property
    def genres(self) -> List[str]:
        return list(filter(None, self.work_info['genres']))

    @property
    def is_nsfw(self) -> bool:
        return self.work_info['isAdult']

    @property
    def poster_url(self) -> str:
        return self.work_info['coverImage']['large']

    @property # Only for animes
    def nb_episodes(self) -> Optional[int]:
        return self.work_info['episodes']

    @property # Only for animes
    def episode_length(self) -> Optional[int]:
        return self.work_info['duration']

    @property # Only for mangas
    def nb_chapters(self) -> Optional[int]:
        return self.work_info['chapters']

    @property
    def status(self) -> AniListStatus:
        return AniListStatus[self.work_info['status']]

    @property # Only for animes
    def studio(self) -> Optional[str]:
        for studio in self.work_info['studios']['edges']:
            if studio['isMain']:
                return studio['node']['name']
        return None

    @property
    def external_links(self) -> Dict[str, str]:
        return {link['site']: link['url'] for link in self.work_info['externalLinks']}

    @property
    def tags(self) -> List[Dict[str, Any]]:
        return [{
            'anilist_tag_id': tag['id'],
            'name': tag['name'],
            'spoiler': tag['isMediaSpoiler'] or tag['isGeneralSpoiler'],
            'votes': tag['rank']
        } for tag in self.work_info['tags']]

    @property
    def staff(self) -> List[AniListStaff]:
        return [
            AniListStaff(
                id=staff['node']['id'],
                name_first=staff['node']['name']['first'],
                name_last=staff['node']['name']['last'],
                role=staff['role']
            ) for staff in self.work_info['staff']['edges']
        ]

    @property
    def relations(self) -> List[Tuple[int, str]]:
        return [
            AniListRelation(
                related_id=relation['node']['id'],
                relation_type=AniListRelationType[relation['relationType']]
            )
            for relation in self.work_info['relations']['edges']
        ]

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.__dict__ == other.__dict__
        return False

    def __hash__(self):
        return hash(tuple(sorted(self.__dict__.items())))

    def __str__(self) -> str:
        return '<AniListEntry {}#{} : {} - {}>'.format(
            self.work_type.name,
            self.anilist_id,
            self.title,
            self.status.value
        )


class AniList:
    BASE_URL = 'https://graphql.anilist.co'

    def __init__(self):
        self._cache = {}

    def _request(self,
                 query: str,
                 variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to AniList's v2 API.
        :param self: an AniList client
        :param query: the GraphQL query string
        :param variables: the GraphQL variables provided for the query
        :type self: AniList
        :type query: str
        :type variables: Dict[str, Any]
        :return: the data returned for this query
        :rtype: Dict[str, Any]
        :raises: an AniListException in case of error
        """

        r = requests.post(
            self.BASE_URL,
            json={
                'query': query,
                'variables': variables
            },
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
        )
        data = r.json()

        if data.get('errors'):
            raise AniListException(data['errors'])

        r.raise_for_status()
        return data['data']

    def get_work(self,
                 search_id: Optional[int] = None,
                 search_title: Optional[str] = None) -> AniListEntry:
        """
        Retrieve a work's information entry from AniList, given an ID or/and a title.
        :param self: an AniList client
        :param search_id: the ID of the work to look for
        :param search_title: the title of the work to look for
        :type self: AniList
        :type search_id: Optional[int]
        :type search_title: Optional[str]
        :return: the entry that was looked for
        :rtype: AniListEntry
        """

        if search_id is None and search_title is None:
            raise ValueError("Please provide an ID or a title")

        variables = {}
        variables.update({'id': search_id} if search_id else {})
        variables.update({'search': search_title} if search_title else {})

        data = self._request(
            query=read_graphql_query(ANILIST_QUERIES['work-info']),
            variables=variables
        )

        if data:
            return AniListEntry(data['Media'], AniListWorkType[data['Media']['type']])
        raise RuntimeError('Malformed JSON, or AniList changed their API.')

    def list_seasonal_animes(self,
                             *,
                             year: Optional[int] = None,
                             season: Optional[AniListSeason] = None,
                             only_airing: Optional[bool] = True,
                             current_page: Optional[int] = 1,
                             per_page: Optional[int] = 50) -> Generator[AniListEntry, None, None]:
        """
        Retrieve a list of entries for a given anime season.
        :param self: an AniList client
        :param year: the year to look for
        :param season: the anime season to look for
        :param only_airing: specify whether or not to look for only airing animes, defaults to True
        :param current_page: the current page, useful when the list is split on multiple pages
        :type self: AniList
        :type year: Optional[int]
        :type season: Optional[AniListSeason]
        :type only_airing: Optional[bool]
        :type current_page: Optional[int]
        :return: a generator for the different work entries for the selected season
        :rtype: Generator[AniListEntry, None, None]
        """

        variables = {}
        variables.update({'season': (season or to_anime_season(datetime.now())).name})
        variables.update({'seasonYear': year or datetime.now().year})
        variables.update({'status': AniListStatus.RELEASING.name} if only_airing else {})
        variables.update({'perPage': per_page})
        variables.update({'page': current_page})

        data = self._request(
            query=read_graphql_query(ANILIST_QUERIES['seasonal-animes']),
            variables=variables
        )

        if not data:
            raise StopIteration

        for anime_info in data['Page']['media']:
            try:
                yield AniListEntry(anime_info, AniListWorkType.ANIME)
            except KeyError:
                raise RuntimeError('Malformed JSON, or AniList changed their API.')

        if data['Page']['pageInfo']['hasNextPage'] and current_page < data['Page']['pageInfo']['lastPage']:
            yield from self.list_seasonal_animes(year=year, season=season, only_airing=only_airing, current_page=current_page+1)

    def get_user_list(self,
                      worktype: AniListWorkType,
                      username: str,
                      current_page: Optional[int] = 1,
                      per_page: Optional[int] = 50) -> Generator[AniListUserEntry, None, None]:
        """
        Retrieve an AniList's user manga or anime list.
        :param self: an AniList client
        :param worktype: the worktype to retrieve, either manga or anime
        :param username: the username of the AniList user to find
        :param current_page: the current page, useful when the list is split on multiple pages
        :type self: AniList
        :type worktype: AniListWorkType
        :type username: str
        :type current_page: Optional[int]
        :return: a generator for the different entries in this user's list (score + work's informations)
        :rtype: Generator[AniListUserEntry, None, None]
        """

        variables = {}
        variables.update({'username': username})
        variables.update({'mediaType': worktype.name})
        variables.update({'perPage': per_page})
        variables.update({'page': current_page})

        data = self._request(
            query=read_graphql_query(ANILIST_QUERIES['user-list']),
            variables=variables
        )

        if not data:
            raise StopIteration

        for list_entry in data['Page']['mediaList']:
            try:
                yield AniListUserEntry(
                    work=AniListEntry(list_entry['media'], worktype),
                    score=int(list_entry['score'])
                )
            except KeyError:
                raise RuntimeError('Malformed JSON, or AniList changed their API.')

        if data['Page']['pageInfo']['hasNextPage'] and current_page < data['Page']['pageInfo']['lastPage']:
            yield from self.get_user_list(worktype, username, current_page+1)


anilist_langs = AniListLanguages()
work_categories = WorkCategories()
staff_roles = StaffRoles()


def build_work_titles(work: Work,
                      titles: Dict[str, Tuple[str, str]]) -> List[WorkTitle]:
    """
    Insert WorkTitle objects for a given Work when required into Mangaki's database.
    :param work: a work
    :param titles: a list of alternative titles
    :type work: Work
    :type titles: Dict[str, Tuple[str, str]]
    :return: a list of WorkTitle objects that were inserted in Mangaki's database
    :rtype: List[WorkTitle]
    """

    if not titles:
        return []

    language_map = {
        'english': anilist_langs.english_ext_lang,
        'romaji': anilist_langs.romaji_ext_lang,
        'japanese': anilist_langs.japanese_ext_lang,
        'unknown': anilist_langs.unknown_ext_lang,
    }
    worktitles = []
    for title, (language, title_type) in titles.items():
        ext_language = language_map.get(language, language_map['unknown'])
        worktitles.append(WorkTitle(
            work=work,
            title=title,
            ext_language=ext_language,
            language=ext_language.lang if ext_language else None,
            type=title_type
        ))

    existing_titles = set(WorkTitle.objects.filter(title__in=titles).values_list('title', flat=True))
    missing_titles = [worktitle for worktitle in worktitles if worktitle.title not in existing_titles]
    WorkTitle.objects.bulk_create(missing_titles)

    return missing_titles

def build_related_works(work: Work,
                        relations: List[Tuple[int, AniListRelationType]]) -> List[RelatedWork]:
    """
    Insert RelatedWork objects for a given Work when required into Mangaki's database.
    This also inserts the related works into the database when they don't exist.
    :param work: a work
    :param relations: a list of related works, with their AniList ID and the relation type
    :type work: Work
    :type relations: List[Tuple[int, AniListRelationType]]
    :return: a list of RelatedWork objects that were inserted in Mangaki's database
    :rtype: List[RelatedWork]
    """

    if not relations:
        return []

    related_works = [
        insert_work_into_database_from_anilist(client.get_work(search_id=related_id))
        for related_id, relation_type in relations
    ]

    existing_relations = RelatedWork.objects.filter(parent_work=work, child_work__in=related_works)
    existing_child_works = set(existing_relations.values_list('child_work__pk', flat=True))
    existing_parent_works = set(existing_relations.values_list('parent_work__pk', flat=True))

    new_relations = [
        RelatedWork(
            parent_work=work,
            child_work=related_works[index],
            type=relation_type.value
        ) for index, (entry, relation_type) in enumerate(relations)
        if related_works[index] is not None
        and related_works[index].pk not in existing_child_works
        and work.pk not in existing_parent_works
    ]

    RelatedWork.objects.bulk_create(new_relations)

    return new_relations

def build_staff(work: Work,
                staff: List[AniListStaff]) -> List[Staff]:
    """
    Insert Artist and Staff objects for a given Work when required into Mangaki's database.
    :param work: a work
    :param staff: a list of staff (and artists) informations
    :type work: Work
    :type staff: List[AniListStaff]
    :return: a list of Staff objects that were inserted in Mangaki's database
    :rtype: List[Staff]
    """

    if not staff:
        return []

    anilist_roles_map = {
        'Director': 'director',
        'Music': 'composer',
        'Original Creator': 'author'
    }

    artists_to_add = []
    artists = []
    for creator in staff:
        name = '{} {}'.format(creator.name_last or '', creator.name_first or '').strip()

        try: # This artist exists : prevent duplicates by updating with the AniList id
            artist = Artist.objects.get(Q(name=name) | Q(anilist_creator_id=creator.id))
            artist.name = name
            artist.anilist_creator_id = creator.id
            artist.save()
            artists.append(artist)
        except Artist.DoesNotExist: # This artist does not yet exist : will be bulk created
            artist = Artist(name=name, anilist_creator_id=creator.id)
            artists_to_add.append(artist)

    artists.extend(Artist.objects.bulk_create(artists_to_add))

    existing_staff_artists = set(s.artist for s in Staff.objects.filter(work=work, artist__in=artists))

    role_map = staff_roles.role_map

    missing_staff = [
        Staff(
           work=work,
           role=role_map.get(anilist_roles_map[creator.role]),
           artist=artists[index]
        ) for index, creator in enumerate(staff) if anilist_roles_map.get(creator.role)
        and artists[index] not in existing_staff_artists
    ]

    Staff.objects.bulk_create(missing_staff)

    return missing_staff

def insert_works_into_database_from_anilist(entries: List[AniListEntry],
                                            build_related: Optional[bool] = True) -> Optional[List[Work]]:
    """
    Insert works into Mangaki's database from AniList data, and return Works inserted.
    :param entries: a list of entries from AniList
    :param build_related: specify whether or not RelatedWorks should be created, defaults to True
    :type entries: List[AniListEntry]
    :type build_related: Optional[bool]
    :return: a list of works effectively added in Mangaki's database (if not already in), or None
    :rtype: Optional[List[Work]]
    """

    category_map = {
        AniListWorkType.ANIME: work_categories.anime,
        AniListWorkType.MANGA: work_categories.manga
    }
    new_works = []

    for entry in entries:
        titles = {synonym: ('unknown', 'synonym') for synonym in entry.synonyms}
        titles.update({entry.title: ('romaji', 'official')})
        titles.update({entry.english_title: ('english', 'main')})
        titles.update({entry.japanese_title: ('japanese', 'official')})

        anime_type = entry.media_format.name if entry.work_type == AniListWorkType.ANIME else ''
        manga_type = entry.media_format.name if entry.work_type == AniListWorkType.MANGA else ''

        # Link Studio and Work
        studio = None
        if entry.studio:
            studio, _ = Studio.objects.get_or_create(title=entry.studio)

        # Create or update the Work entry in the database
        work, created_work = Work.objects.update_or_create(
            title__in=titles,
            category__slug=entry.work_type.value,
            defaults={
                'category': category_map.get(entry.work_type),
                'title': entry.title,
                'ext_poster': entry.poster_url,
                'nsfw': entry.is_nsfw,
                'date': entry.start_date,
                'end_date': entry.end_date,
                'ext_synopsis': entry.description or '',
                'nb_episodes': entry.nb_episodes or entry.nb_chapters,
                'anime_type': anime_type,
                'manga_type': manga_type,
                'studio': studio
            }
        )

        # Build genres for this Work
        genres = [Genre.objects.get_or_create(title=genre)[0] for genre in entry.genres]
        work.genre.set(genres, bulk=True, clear=(not created_work))

        # Create WorkTitle entries in the database for this Work
        build_work_titles(work, titles)

        # Build RelatedWorks (and add those Works too) if wanted
        if build_related:
            build_related_works(work, entry.relations)

        # Build Artist and Staff
        build_staff(work, entry.staff)

        # Save the Work object and add a Reference
        work.save()
        Reference.objects.get_or_create(work=work, url=entry.anilist_url)
        new_works.append(work)

    return new_works if new_works else None

def insert_work_into_database_from_anilist(entry: AniListEntry,
                                           build_related: Optional[bool] = True) -> Optional[Work]:
    """
    Insert a single work into Mangaki's database from AniList data, and return Work inserted.
    :param entry: an entry from AniList
    :param build_related: specify whether or not RelatedWorks should be created, defaults to True
    :type entries: AniListEntry
    :type build_related: Optional[bool]
    :return: a work effectively added in Mangaki's database (if not already in), or None
    :rtype: Optional[Work]
    """

    work_result = insert_works_into_database_from_anilist([entry], build_related)
    return work_result[0] if work_result else None
