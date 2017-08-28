from datetime import datetime
from enum import Enum
from collections import namedtuple
from typing import Dict, List, Tuple, Optional, Any, Generator
from urllib.parse import urljoin
import time

import requests
from django.utils.functional import cached_property
from django.db.models import Q

from mangaki import settings
from mangaki.models import (Work, RelatedWork, WorkTitle, Reference, Category,
                            ExtLanguage, Studio, Genre, Artist, Staff, Role)


def to_python_datetime(date):
    """
    Converts AniList's fuzzydate to Python datetime format.
    >>> to_python_datetime('20150714')
    datetime.datetime(2015, 7, 14, 0, 0)
    >>> to_python_datetime('20150700')
    datetime.datetime(2015, 7, 1, 0, 0)
    >>> to_python_datetime('20150000')
    datetime.datetime(2015, 1, 1, 0, 0)
    >>> to_python_datetime('2015')
    Traceback (most recent call last):
     ...
    ValueError: no valid date format found for 2015
    """
    date = str(date).strip()
    for fmt in ('%Y%m%d', '%Y%m00', '%Y0000'):
        try:
            return datetime.strptime(date, fmt)
        except ValueError:
            pass
    raise ValueError('no valid date format found for {}'.format(date))

def to_anime_season(date):
    """
    Return the season corresponding to a date
    >>> to_anime_season(datetime.datetime(2017, 3, 3, 0, 0))
    'winter'
    """
    if 1 <= date.month <= 3:
        return 'winter'
    elif 4 <= date.month <= 6:
        return 'spring'
    elif 7 <= date.month <= 9:
        return 'summer'
    else:
        return 'fall'

def is_no_results(anilist_error):
    """
    Return True is the error is a 'no results' error, False else
    """
    if isinstance(anilist_error, dict) and anilist_error.get('messages'):
        for message in anilist_error['messages']:
            message = message.lower()
            if 'no query results' in message or 'no results' in message:
                return True

    return False

def is_route_not_found(anilist_error):
    """
    Return True is the error is a 'no such API route found' error, False else
    """
    if isinstance(anilist_error, dict) and anilist_error.get('messages'):
        for message in anilist_error['messages']:
            message = message.lower()
            if 'api route not found' in message:
                return True

    return False

def is_token_error(anilist_error):
    """
    Return True is the error is a 'no token or token expired' error, False else
    """
    return anilist_error in ('unauthorized', 'access_denied')


class AniListException(Exception):
    """
    This class defines a custom Exception for errors with the AniList's API
    """

    def __init__(self, error):
        super().__init__()
        if isinstance(error, dict):
            self.args = ['{} - {}'.format(k, v) for k, v in error.items()]
        else:
            self.args = [error]

    def __str__(self):
        return ', '.join(self.args)


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
        return Category.objects.get(slug=AniListWorks.animes.value)

    @cached_property
    def manga(self) -> Category:
        return Category.objects.get(slug=AniListWorks.mangas.value)


class StaffRoles:
    @cached_property
    def role_map(self) -> Dict[str, Role]:
        return {role.slug: role for role in Role.objects.all()}


class AniListWorks(Enum):
    """
    This class enumerates the different kinds of works found on AniList
    """

    animes = 'anime'
    mangas = 'manga'


class AniListStatus(Enum):
    """
    This class enumerates the different kinds of airing (or publising) statuses
    for animes (or mangas) on AniList
    """

    aired = 'finished airing'
    airing = 'currently airing'
    published = 'finished publishing'
    publishing = 'publishing'
    anime_coming = 'not yet aired'
    manga_coming = 'not yet published'
    cancelled = 'cancelled'


class AniListRelationType(Enum):
    """
    This class enumerates the different kinds of relations between works found
    on AniList
    """

    sequel = 'sequel'
    prequel = 'prequel'
    side_story = 'side story'
    parent_story = 'parent'
    summary = 'summary'
    adaptation = 'adaptation'


class AniListEntry:
    """
    This class stores informations for AniList entries given a JSON for this
    entry. This is useful for every entry on AniList since it retrieves the
    more basic informations given by AniList's series models.
    Sometimes, tags are also included and are stored in this class too.
    """

    def __init__(self, work_info, work_type: AniListWorks):
        self.work_info = work_info
        self.work_type = work_type

        if self.work_info['series_type'] != work_type.value:
            raise ValueError('AniList data not from {}'.format(work_type.value))

    @property
    def anilist_id(self) -> int:
        return self.work_info['id']

    @property
    def anilist_url(self) -> int:
        return 'https://anilist.co/{}/{}/'.format(self.work_type.value, self.anilist_id)

    @property
    def title(self) -> str:
        return self.work_info['title_romaji']

    @property
    def english_title(self) -> str:
        return self.work_info['title_english']

    @property
    def japanese_title(self) -> str:
        return self.work_info['title_japanese']

    @property
    def media_type(self) -> str:
        return self.work_info['type']

    @property
    def start_date(self) -> Optional[datetime]:
        if self.work_info['start_date_fuzzy']:
            return to_python_datetime(self.work_info['start_date_fuzzy'])
        return None

    @property
    def end_date(self) -> Optional[datetime]:
        if self.work_info['end_date_fuzzy']:
            return to_python_datetime(self.work_info['end_date_fuzzy'])
        return None

    @property
    def description(self) -> Optional[str]:
        return self.work_info.get('description')

    @property
    def synonyms(self) -> List[str]:
        return list(filter(None, self.work_info['synonyms']))

    @property
    def genres(self) -> List[str]:
        return list(filter(None, self.work_info['genres']))

    @property
    def is_nsfw(self) -> bool:
        return self.work_info['adult']

    @property
    def poster_url(self) -> str:
        return self.work_info['image_url_lge']

    @property
    def nb_episodes(self) -> int:
        if self.work_type == AniListWorks.animes:
            return self.work_info['total_episodes']
        return 0

    @property
    def episode_length(self) -> Optional[int]:
        if self.work_type == AniListWorks.animes:
            return self.work_info.get('duration')
        return None

    @property
    def nb_chapters(self) -> int:
        if self.work_type == AniListWorks.mangas:
            return self.work_info['total_chapters']
        return 0

    @property
    def status(self) -> Optional[AniListStatus]:
        if self.work_type == AniListWorks.animes:
            return AniListStatus(self.work_info['airing_status'])
        elif self.work_type == AniListWorks.mangas:
            return AniListStatus(self.work_info['publishing_status'])
        return None

    @property
    def tags(self) -> Optional[List[Dict[str, Any]]]:
        if not self.work_info.get('tags'):
            return []

        return [{
            'name': tag['name'],
            'anilist_tag_id': tag['id'],
            'spoiler': tag['spoiler'] or tag['series_spoiler'],
            'votes': tag['votes']
        } for tag in self.work_info['tags']]

    def __str__(self) -> str:
        return '<AniListEntry {}#{} : {} - {}>'.format(
            self.work_type.value,
            self.anilist_id,
            self.title,
            self.status.value
        )


class AniListRichEntry(AniListEntry):
    """
    This class stores more informations for AniList entries, when such
    additional information is available. It's most useful when retrieving an
    entry by its AniList ID : characters, staff, reviews, relations, anime or
    manga relations, studios and even external links are provided in that case.
    """

    def __init__(self, work_info, work_type: AniListWorks):
        super().__init__(work_info, work_type)
        self._build_external_links()

    @property
    def studio(self) -> Optional[str]:
        if self.work_info.get('studio'):
            for studio in self.work_info.get('studio'):
                if studio['main_studio'] == 1:
                    return studio['studio_name']
        return None

    @property
    def youtube_url(self) -> Optional[str]:
        if self.work_info.get('youtube_id'):
            return 'https://www.youtube.com/watch?v={}'.format(self.work_info['youtube_id'])
        return None

    def _build_external_links(self):
        if self.work_info.get('external_links'):
            for link in self.work_info.get('external_links'):
                if link['site'] == 'Crunchyroll':
                    self.crunchyroll_url = link['url']
                elif link['site'] == 'Twitter':
                    self.twitter_url = link['url']
                elif link['site'] == 'Official Site':
                    self.official_url = link['url']

    @property
    def staff(self) -> List[Tuple[AniListEntry, str]]:
        staff_members = []
        if self.work_info.get('staff'):
            for staff in self.work_info['staff']:
                staff_members.append(AniListStaff(
                    id=staff['id'],
                    name_first=staff['name_first'],
                    name_last=staff['name_last'],
                    role=staff['role']
                ))
        return staff_members

    @property
    def relations(self) -> List[Tuple[AniListEntry, str]]:
        related_works = []
        if self.work_info.get('relations'):
            for relation in self.work_info['relations']:
                related_works.append((
                    AniListEntry(relation, self.work_type),
                    AniListRelationType(relation['relation_type'])
                ))
        return related_works


AniListUserEntry = namedtuple('AniListUserEntry', ('work', 'score'))
AniListStaff = namedtuple('AniListStaff', ('id', 'name_first', 'name_last', 'role'))


class AniList:
    BASE_URL = "https://anilist.co/api/"
    AUTH_PATH = "auth/access_token"

    def __init__(self,
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None):
        if not client_id or not client_secret:
            self.is_available = False
        else:
            self.is_available = True

            self.client_id = client_id
            self.client_secret = client_secret

            self._cache = {}
            self._session = requests.Session()
            self._auth = None

    def _authenticate(self):
        if not self.is_available:
            raise RuntimeError('AniList API is not available!')

        params = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        r = self._session.post(urljoin(self.BASE_URL, self.AUTH_PATH), data=params)
        r.raise_for_status()

        self._auth = r.json()
        self._session.headers['Authorization'] = 'Bearer ' + self._auth['access_token']

        return self._auth

    def _is_authenticated(self):
        if not self.is_available:
            return False
        if self._auth is None:
            return False
        return self._auth['expires'] > time.time()

    def _request(self,
                 datapage: str,
                 params: Optional[Dict[str, str]] = None,
                 query_params: Optional[Dict[str, str]] = None):
        """
        Request an Anilist API's page (see https://anilist-api.readthedocs.io/en/latest/ for more)
        >>> self._request("{series_type}/{id}", params={"series_type": "anime", "id": "5"})
        Returns a series model as a JSON.
        >>> self._request("browse/{series_type}", params={"series_type": "anime"}, query_params={"year": "2017"})
        Returns up to 40 small series models where year is 2017 as a JSON.
        """
        if not self._is_authenticated():
            self._authenticate()

        if params is None:
            params = {}

        if query_params is None:
            query_params = {}

        r = self._session.get(urljoin(self.BASE_URL, datapage.format(**params)), params=query_params)
        data = r.json()

        if not isinstance(data, list) and data.get('error'):
            if is_no_results(data['error']):
                return None
            elif is_route_not_found(data['error']):
                raise AniListException('"{}" API route does not exist'.format(datapage))
            elif is_token_error(data['error']):
                raise AniListException('token no longer valid or not found')
            else:
                raise AniListException(data['error'])

        r.raise_for_status()
        return data

    def list_seasonal_animes(self,
                             *,
                             only_airing: Optional[bool] = True,
                             year: Optional[int] = None,
                             season: Optional[str] = None) -> Generator[AniListEntry, None, None]:
        if not year or not season:
            now = datetime.now()
            year = now.year
            season = to_anime_season(now)

        query_params = {'year': year, 'season': season, 'full_page': 'true'}

        if only_airing:
            query_params.update({'status': AniListStatus.airing.value})

        data = self._request('browse/anime', query_params=query_params)
        for anime_info in data:
            yield AniListEntry(anime_info, AniListWorks.animes)

    def get_work_by_id(self,
                       worktype: AniListWorks,
                       id: int) -> AniListRichEntry:
        """
        Search a work by ID on AniList and returns a rich entry if the ID exists,
        or None if there are no results.
        A rich entry has informations about characters, staff, studio and even
        related works.
        """
        data = self._request(
            '{worktype}/{id}/page',
            {'worktype': worktype.value, 'id': id}
        )

        if data:
            return AniListRichEntry(data, worktype)
        return None

    def get_work_by_title(self,
                          worktype: AniListWorks,
                          title: str) -> AniListEntry:
        """
        Search a work by title on AniList and returns the first result if there
        are results, or None if there are no results.
        AniList searches a work by romaji, English or Japanese title and even
        by synonym titles.
        """
        data = self._request(
            '{worktype}/search/{title}',
            {'worktype': worktype.value, 'title': title}
        )

        if data:
            return AniListEntry(data[0], worktype)
        return None

    def get_user_list(self,
                      worktype: AniListWorks,
                      username: str) -> Generator[AniListUserEntry, None, None]:
        data = self._request(
            'user/{username}/{worktype}list',
            {'username': username, 'worktype': worktype.value}
        )

        if not data:
            raise StopIteration

        for list_type in data['lists']:
            for list_entry in data['lists'][list_type]:
                try:
                    yield AniListUserEntry(
                        work=AniListEntry(list_entry[worktype.value], worktype),
                        score=int(list_entry['score'])
                    )
                except KeyError:
                    raise RuntimeError('Malformed JSON, or AniList changed their API.')


client = AniList(
    getattr(settings, 'ANILIST_CLIENT', None),
    getattr(settings, 'ANILIST_SECRET', None)
)

anilist_langs = AniListLanguages()
language_map = {
    'english': anilist_langs.english_ext_lang,
    'romaji': anilist_langs.romaji_ext_lang,
    'japanese': anilist_langs.japanese_ext_lang,
    'unknown': anilist_langs.unknown_ext_lang,
}

work_categories = WorkCategories()
category_map = {
    AniListWorks.animes: work_categories.anime,
    AniListWorks.mangas: work_categories.manga
}

staff_roles = StaffRoles()
role_map = staff_roles.role_map

def insert_works_into_database_from_anilist(entries: List[AniListEntry]) -> Optional[List[Work]]:
    """
    Insert works into Mangaki database from AniList data, and return Works added.
    :param entries: a list of entries from AniList to insert if not present in the database
    :type entries: List[AniListEntry]
    :return: a list of works effectively added in the Mangaki database
    :rtype: Optional[List[Work]]
    """
    new_works = []

    for entry in entries:
        titles = {synonym: ('unknown', 'synonym') for synonym in entry.synonyms}
        titles.update({entry.title: ('romaji', 'official')})
        titles.update({entry.english_title: ('english', 'main')})
        titles.update({entry.japanese_title: ('japanese', 'official')})

        anime_type = entry.media_type if entry.work_type == AniListWorks.animes else ''
        manga_type = entry.media_type if entry.work_type == AniListWorks.mangas else ''

        studio = None

        category = category_map.get(entry.work_type, None)

        work_present_in_db = Work.objects.filter(
            category__slug=entry.work_type.value,
            title__in=titles
        )

        # If one of this entry's title match in the database, skip it
        if work_present_in_db:
            continue

        # Link Studio and Work [AniListRichEntry only]
        if isinstance(entry, AniListRichEntry) and entry.studio:
            studio, created = Studio.objects.get_or_create(title=entry.studio)

        # Create the Work entry in the database
        work = Work.objects.create(
            category=category,
            title=entry.title,
            ext_poster=entry.poster_url,
            nsfw=entry.is_nsfw,
            date=entry.start_date,
            end_date=entry.end_date,
            ext_synopsis=(entry.description if entry.description else ''),
            nb_episodes=(entry.nb_episodes or entry.nb_chapters),
            anime_type=anime_type,
            manga_type=manga_type,
            studio=studio
        )

        # Build genres for this Work
        for genre_title in entry.genres:
            genre, created = Genre.objects.get_or_create(title=genre_title)
            work.genre.add(genre)

        # Create WorkTitle entries in the database for this Work
        current_work_titles = [
            WorkTitle(
                work=work,
                title=title,
                ext_language=language_map[language],
                language=language_map[language].lang,
                type=title_type
            ) for title, (language, title_type) in titles.items()
        ]
        WorkTitle.objects.bulk_create(current_work_titles)

        # Build RelatedWorks (and add those Works too) [AniListRichEntry only]
        if isinstance(entry, AniListRichEntry) and entry.relations:
            new_relations = []

            for work_related, relation_type in entry.relations:
                added_work = insert_works_into_database_from_anilist([work_related])
                if not added_work:
                    continue

                new_relations.append(
                    RelatedWork(
                        parent_work=work,
                        child_work=added_work[0],
                        type=relation_type.name
                    )
                )

            RelatedWork.objects.bulk_create(new_relations)

        # Build Artist and Staff [AniListRichEntry only]
        if isinstance(entry, AniListRichEntry) and entry.staff:
            anilist_roles_map = {
                'Director': 'director',
                'Music': 'composer',
                'Original Creator': 'author'
            }

            artists_to_add = []
            artists = []
            for creator in entry.staff:
                name = '{} {}'.format(creator.name_last, creator.name_first)
                artist = Artist.objects.filter(Q(name=name) | Q(anilist_creator_id=creator.id)).first()

                if not artist: # This artist does not yet exist : will be bulk created
                   artist = Artist(name=name, anilist_creator_id=creator.id)
                   artists_to_add.append(artist)
                else: # This artist exists : prevent duplicates by updating with the AniDB id
                   artist.name = name
                   artist.anilist_creator_id = creator.id
                   artist.save()
                   artists.append(artist)

            artists.extend(Artist.objects.bulk_create(artists_to_add))

            staffs = []
            for index, creator in enumerate(entry.staff):
                role_slug = anilist_roles_map.get(creator.role)
                if role_slug:
                    staffs.append(Staff(
                       work=work,
                       role=role_map.get(role_slug),
                       artist=artists[index]
                    ))

            existing_staff = set(Staff.objects
                                .filter(work=work,
                                        artist__in=[artist for artist in artists])
                                .values_list('work', 'role', 'artist'))

            missing_staff = [
                staff for staff in staffs
                if (staff.work, staff.role, staff.artist) not in existing_staff
            ]

            Staff.objects.bulk_create(missing_staff)

        # Save the Work object and add a Reference
        work.save()
        Reference.objects.create(work=work, url=entry.anilist_url)
        new_works.append(work)

    return new_works if new_works else None

def insert_work_into_database_from_anilist(entry: AniListEntry) -> Optional[Work]:
    work_result = insert_works_into_database_from_anilist([entry])
    return work_result[0] if work_result else None
