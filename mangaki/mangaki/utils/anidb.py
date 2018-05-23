from datetime import datetime
from collections import namedtuple
from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.core.exceptions import MultipleObjectsReturned
from django.utils.functional import cached_property
from django.db.models import Q

from mangaki import settings
from mangaki.models import (
    Work,
    WorkTitle,
    Category,
    ExtLanguage,
    Role,
    Staff,
    Studio,
    Artist,
    Tag,
    TaggedWork,
    RelatedWork,
    Reference
)


def to_python_datetime(date):
    """
    Converts AniDB's XML date YYYY-MM-DD to Python datetime format.
    >>> to_python_datetime('2015-07-14')
    datetime.datetime(2015, 7, 14, 0, 0)
    >>> to_python_datetime('2015-07')
    datetime.datetime(2015, 7, 1, 0, 0)
    >>> to_python_datetime('2015')
    datetime.datetime(2015, 1, 1, 0, 0)
    >>> to_python_datetime('2015-25')
    Traceback (most recent call last):
     ...
    ValueError: no valid date format found for 2015-25
    """
    date = date.strip()
    for fmt in ('%Y-%m-%d', '%Y-%m', '%Y'):
        try:
            return datetime.strptime(date, fmt)
        except ValueError:
            pass
    raise ValueError('no valid date format found for {}'.format(date))

AniDBTag = namedtuple('AniDBTag', ['title', 'weight', 'anidb_tag_id'])


class AniDB:
    BASE_URL = "http://api.anidb.net:9001/httpapi"
    SEARCH_URL = "http://anisearch.outrance.pl/"
    PROTOCOL_VERSION = 1

    def __init__(self,
                 client_id: Optional[str] = None,
                 client_ver: Optional[int] = None):
        if not client_id or not client_ver:
            self.is_available = False
        else:
            self.client_id = client_id
            self.client_ver = client_ver
            self._cache = {}
            self.is_available = True

    def _request(self, datapage, params=None):
        if not self.is_available:
            raise RuntimeError('AniDB API is not available!')

        if params is None:
            params = {}

        params.update({
            'client': self.client_id,
            'clientver': self.client_ver,
            'protover': self.PROTOCOL_VERSION,
            'request': datapage
        })

        r = requests.get(self.BASE_URL, params=params)
        r.raise_for_status()
        return r

    # Anime http://wiki.anidb.net/w/HTTP_API_Definition#Access

    def search(self, q):
        """
        Search for `aid`s by anime title using service provided by eloyard.
        http://anisearch.outrance.pl/doc.html
        """
        r = requests.get(self.SEARCH_URL, params={
            'task': "search",
            'query': q,
        })
        r.raise_for_status()
        results = []
        animetitles = BeautifulSoup(r.text, 'xml').animetitles
        for anime in animetitles.find_all('anime'):
            results.append({
                'id': int(anime['aid']),
                'title': str(anime.find('title', attrs={'type': "official"}).string)
            })

        return results

    @cached_property
    def anime_category(self) -> Category:
        return Category.objects.get(slug='anime')

    @cached_property
    def lang_map(self) -> Dict[str, ExtLanguage]:
        ext_langs = ExtLanguage.objects.filter(source='anidb').select_related('lang')
        return {ext.lang.code: ext for ext in ext_langs}

    @cached_property
    def role_map(self) -> Dict[str, Role]:
        return {role.slug: role for role in Role.objects.all()}

    @cached_property
    def unknown_language(self) -> ExtLanguage:
        return ExtLanguage.objects.get(source='anidb', ext_lang='x-unk')

    def get_xml(self, anidb_aid: int):
        """Return the XML file for an anime from AniDB given its AniDB ID"""

        r = self._request("anime", {'aid': anidb_aid})
        soup = BeautifulSoup(r.text.encode('utf-8'), 'xml')
        if soup.error is not None:
            raise Exception(soup.error.string)

        return soup.anime

    def get_titles(self,
                   anidb_aid: Optional[int] = None,
                   titles_soup: Optional[str] = None) -> Tuple[List[Dict[str, str]], str]:
        """ Get the list of titles and the main title for an anime given the the
        AniDB ID or the XML string containing titles.

        Return : List[{'title': str, 'lang': str, 'type': str}], str
        """
        if anidb_aid is not None:
            anime = self.get_xml(anidb_aid)
            titles_soup = anime.titles

        main_title = None
        titles = []
        for title_node in titles_soup.find_all('title'):
            title = str(title_node.string).strip()
            lang = title_node.get('xml:lang')
            title_type = title_node.get('type')

            titles.append({
                'title': title,
                'lang': lang,
                'type': title_type
            })

            if title_type == 'main':
                main_title = title

        return titles, main_title

    def _build_work_titles(self,
                           work: Work,
                           titles: Dict[str, Dict[str, str]],
                           reload_lang_cache: bool = False) -> List[WorkTitle]:
        if reload_lang_cache:
            del self.lang_map

        work_titles = []
        raw_titles = []
        for title_info in titles:
            title = title_info['title']
            lang = title_info['lang']
            title_type = title_info['type']

            ext_lang_model = self.lang_map.get(lang, self.unknown_language)
            raw_titles.append(title)
            work_titles.append(
                WorkTitle(
                    work=work,
                    title=title,
                    ext_language=ext_lang_model,
                    language=ext_lang_model.lang if ext_lang_model else None,
                    type=title_type
                )
            )

        already_existing_titles = set(WorkTitle.objects
                                      .filter(title__in=raw_titles)
                                      .values_list('title', flat=True))

        missing_titles = [
            work_title
            for work_title in work_titles
            if work_title.title not in already_existing_titles
        ]

        WorkTitle.objects.bulk_create(missing_titles)

        return missing_titles

    def get_creators(self,
                     anidb_aid: Optional[int] = None,
                     creators_soup: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Studio]:
        """ Get the list of staff and the studio for an anime given the the
        AniDB ID or the XML string containing creators.

        Return : List[{'role': Role, 'name': str, 'anidb_creator_id': int}], Studio
        """
        if anidb_aid is not None:
            anime = self.get_xml(anidb_aid)
            creators_soup = anime.creators

        creators = []
        studio = None
        if creators_soup is not None:
            for creator_node in creators_soup.find_all('name'):
                creator_name = str(creator_node.string).strip()
                creator_id = creator_node.get('id')
                creator_type = creator_node.get('type')
                role_slug = None

                if creator_type == 'Direction':
                    role_slug = 'director'
                elif creator_type == 'Music':
                    role_slug = 'composer'
                elif creator_type == 'Original Work' or creator_type == 'Story Composition':
                    role_slug = 'author'
                elif creator_type == 'Animation Work' or creator_type == 'Work':
                    # AniDB marks Studio as such a creator's type
                    studio = Studio.objects.filter(title=creator_name).first()
                    if studio is None:
                        studio = Studio(title=creator_name)
                        studio.save()

                if role_slug is not None:
                    creators.append({
                        'role': self.role_map.get(role_slug),
                        'name': creator_name,
                        'anidb_creator_id': creator_id
                    })

        return creators, studio

    def _build_staff(self,
                     work: Work,
                     creators: List[Dict[str, Any]],
                     reload_role_cache: bool = False) -> List[Staff]:
        if reload_role_cache:
            del self.role_map

        processed_anidb_aids = []
        artists_to_add = []
        artists_list = []
        for nc in creators:
            artist = Artist.objects.filter(Q(name=nc["name"]) | Q(anidb_creator_id=nc["anidb_creator_id"])).first()

            if nc["anidb_creator_id"] in processed_anidb_aids:  # Skip if this artist has more than one role
                continue

            if not artist:  # This artist does not yet exist : will be bulk created
                artist = Artist(name=nc["name"], anidb_creator_id=nc["anidb_creator_id"])
                artists_to_add.append(artist)
            else:  # This artist exists : prevent duplicates by updating with the AniDB id
                artist.name = nc["name"]
                artist.anidb_creator_id = nc["anidb_creator_id"]
                artist.save()
                artists_list.append(artist)
            processed_anidb_aids.append(nc["anidb_creator_id"])

        artists_list.extend(Artist.objects.bulk_create(artists_to_add))
        artists = {artist.name: artist for artist in artists_list}

        existing_staff = set(Staff.objects.filter(work=work,
                                role__in=(nc["role"] for nc in creators),
                                artist__name__in=(nc["name"] for nc in creators))
                                .values_list('work', 'role', 'artist'))
        missing_staff = [
            Staff(
                work=work,
                role=nc["role"],
                artist=artists[nc["name"]]
            ) for nc in creators if (work.pk, nc["role"].pk, artists[nc["name"]].pk) not in existing_staff
        ]

        Staff.objects.bulk_create(missing_staff)
        return missing_staff

    def get_tags(self,
                 anidb_aid: Optional[int] = None,
                 tags_soup: Optional[str] = None) -> List[AniDBTag]:
        """ Get the list of tags for an anime given the the AniDB ID or the XML
        string containing tags.

        Return : List[AniDBTag]
        """
        if anidb_aid is not None:
            anime = self.get_xml(anidb_aid)
            tags_soup = anime.tags

        if tags_soup is None:
            return []

        tags = []
        for tag_node in tags_soup.find_all('tag'):
            tag_title = str(tag_node.find('name').string).strip()
            tag_id = int(tag_node.get('id'))
            tag_weight = int(tag_node.get('weight'))
            tag_verified = tag_node.get('verified').lower() == 'true'

            if tag_verified:
                tags.append(
                    AniDBTag(
                        title=tag_title,
                        weight=tag_weight,
                        anidb_tag_id=tag_id
                    )
                )

        return tags

    def update_tags(self,
                    work: Work,
                    anidb_tags: List[AniDBTag]):
        tags_diff = diff_between_anidb_and_local_tags(work, anidb_tags)

        deleted_tags = tags_diff['deleted_tags']
        added_tags = tags_diff['added_tags']
        updated_tags = tags_diff['updated_tags']
        kept_tags = tags_diff['kept_tags']
        all_tags = deleted_tags + added_tags + updated_tags + kept_tags

        tags_ids = [tag.anidb_tag_id for tag in all_tags]
        deleted_tags_ids = [tag.anidb_tag_id for tag in deleted_tags]

        existing_tags = Tag.objects.filter(anidb_tag_id__in=tags_ids).all()
        existing_tags_id = set(existing_tags.values_list('anidb_tag_id', flat=True))

        # New tags have to be added to the database (if they aren't already present)
        tags_weight = {}
        tags_to_add = []
        tags_list = []
        for tag in added_tags:
            tags_weight[tag.anidb_tag_id] = tag.weight
            if tag.anidb_tag_id not in existing_tags_id:
                tag_to_add = Tag(title=tag.title, anidb_tag_id=tag.anidb_tag_id)
                tags_to_add.append(tag_to_add)
                tags_list.append(tag_to_add)
            else:
                existing_tag = existing_tags.filter(anidb_tag_id=tag.anidb_tag_id).first()
                tags_list.append(existing_tag)
        Tag.objects.bulk_create(tags_to_add)

        # Assign tags to the work via TaggedWork
        tagged_works_to_add = []
        for tag in tags_list:
            tag_weight = tags_weight[tag.anidb_tag_id]
            tagged_work = TaggedWork(tag=tag, work=work, weight=tag_weight)
            tagged_works_to_add.append(tagged_work)
        TaggedWork.objects.bulk_create(tagged_works_to_add)

        # Update the weight of tags that already exist (only if the weight changed)
        for tag in updated_tags:
            tagged_work = work.taggedwork_set.get(tag__title=tag.title)
            tagged_work.weight = tag.weight
            tagged_work.save()

        # Finally, remove a tag from a work if it no longer exists on AniDB's side
        TaggedWork.objects.filter(work=work, tag__anidb_tag_id__in=deleted_tags_ids).delete()

    def get_related_animes(self,
                           anidb_aid: Optional[int] = None,
                           related_animes_soup: Optional[str] = None) -> Dict[int, Dict[str, str]]:
        """ Get the list of related animes given the the AniDB ID or the XML
        string containing related animes.

        Return : Dict[related_anime_id: {'title': str, 'type': str}]

        relation type is one of 'prequel', 'sequel', 'summary', 'side_story',
        'parent_story', 'alternative_setting', 'same_setting' or 'other'
        """
        if anidb_aid is not None:
            anime = self.get_xml(anidb_aid)
            related_animes_soup = anime.relatedanime

        related_animes = {}
        if related_animes_soup is not None:
            for related_node in related_animes_soup.find_all('anime'):
                related_anidb_id = int(related_node.get('id'))
                related_title = str(related_node.string).strip()
                related_type = str(related_node.get('type')).strip()
                related_type = related_type.lower().replace(" ", "_")

                related_animes[related_anidb_id] = {
                    'title': related_title,
                    'type': related_type
                }

        return related_animes

    def _build_related_animes(self,
                              work: Work,
                              related_animes: Dict[int, Dict[str, str]]) -> List[RelatedWork]:
        anidb_aids = related_animes.keys()

        # Fill the Work database with missing work items and retrieve existing ones
        # Note : these works won't be filled with data, they'll have to be updated afterwards
        existing_works = Work.objects.filter(anidb_aid__in=anidb_aids)
        existing_anidb_aids = set(existing_works.values_list('anidb_aid', flat=True))

        new_works = []
        for anidb_aid in anidb_aids:
            if anidb_aid not in existing_anidb_aids:
                new_works.append(
                    Work(
                        title=related_animes[anidb_aid]['title'],
                        category=self.anime_category,
                        anidb_aid=anidb_aid
                    )
                )

        works = [work for work in existing_works]
        works.extend(Work.objects.bulk_create(new_works))

        # Add relations between works if they don't yet exist
        existing_relations = RelatedWork.objects.filter(child_work__in=works, parent_work=work)
        existing_child_works = set(existing_relations.values_list('child_work__pk', flat=True))
        existing_parent_works = set(existing_relations.values_list('parent_work__pk', flat=True))

        new_relations = []
        for child_work in works:
            if child_work.pk not in existing_child_works and work.pk not in existing_parent_works:
                new_relations.append(
                    RelatedWork(
                        parent_work=work,
                        child_work=child_work,
                        type=related_animes[child_work.anidb_aid]['type']
                    )
                )

        RelatedWork.objects.bulk_create(new_relations)

        return new_relations

    def get_or_update_work(self,
                           anidb_aid: int,
                           reload_lang_cache: bool = False,
                           reload_role_cache: bool = False) -> Work:
        """
        Use `get_dict` internally to create (in the database) the bunch of objects you need to create a work.

        Cache internally intermediate models objects (e.g. Language, ExtLanguage, Category, Role)

        This won't return already existing WorkTitle attached to the Work object.

        :param anidb_aid: the AniDB identifier
        :type anidb_aid: integer
        :param reload_lang_cache: forcefully reload the ExtLanguage cache,
            if it has changed since the instantiation of the AniDB client (default: false).
        :param reload_role_cache: forcefully reload the Role cache,
            if it has changed since the instantiation of the AniDB client (default: false).
        :type reload_lang_cache: boolean
        :type reload_role_cache: boolean
        :return: the Work object related to the AniDB ID passed in parameter,
            None if two or more Work objects match the AniDB ID provided.
        :rtype: a `mangaki.models.Work` object.
        """

        anime = self.get_xml(anidb_aid)

        titles, main_title = self.get_titles(titles_soup=anime.titles)
        creators, studio = self.get_creators(creators_soup=anime.creators)
        tags = self.get_tags(tags_soup=anime.tags)
        related_animes = self.get_related_animes(related_animes_soup=anime.relatedanime)
        url = str(anime.url.string) if anime.url else None

        anime = {
            'title': main_title,
            'source': 'AniDB: ' + url or '',
            'ext_poster': urljoin('http://img7.anidb.net/pics/anime/', str(anime.picture.string)) if anime.picture else '',
            'nsfw': anime.get('restricted') == 'true',
            'date': to_python_datetime(anime.startdate.string),
            'end_date': to_python_datetime(anime.enddate.string) if anime.enddate else None,
            'ext_synopsis': str(anime.description.string) if anime.description else '',
            'nb_episodes': int(anime.episodecount.string) if anime.episodecount else None,
            'anime_type': str(anime.type.string) if anime.type else None,
            'anidb_aid': anidb_aid,
            'studio': studio
        }

        try:
            work, created = Work.objects.update_or_create(category=self.anime_category,
                                                          anidb_aid=anidb_aid,
                                                          defaults=anime)
        except MultipleObjectsReturned:
            return None

        self._build_work_titles(work, titles, reload_lang_cache)
        self._build_staff(work, creators, reload_role_cache)
        self.update_tags(work, tags)

        if created and is_nsfw_based_on_anidb_tags(tags):
            work.nsfw = True
            work.save()

        if created:
            self._build_related_animes(work, related_animes)
            # Theorically, there should be no other reference than this one.
            Reference.objects.create(
                work=work,
                source='AniDB',
                identifier=anidb_aid,
                url=url
            )

        return work

client = AniDB(
    getattr(settings, 'ANIDB_CLIENT', 'test_client'),
    getattr(settings, 'ANIDB_VERSION', 1)
)  # FIXME: Such a thing should not exist. It should be created in the test.

def diff_between_anidb_and_local_tags(work: Work,
                                      anidb_tags: List[AniDBTag]) -> Dict[str, List[AniDBTag]]:
    """
    Return a Dict containing the difference (ie. added, updated, deleted or kept
    tags) between AniDB's tags and local tags.
    """

    tag_work_list = TaggedWork.objects.filter(work=work).all()
    values = tag_work_list.values_list('tag__title', 'weight', 'tag__anidb_tag_id')
    current_tags = [AniDBTag(title=v[0], weight=v[1], anidb_tag_id=v[2]) for v in values]

    deleted_tags = list(set(current_tags) - set(anidb_tags))
    added_tags = list(set(anidb_tags) - set(current_tags))
    kept_tags = list(set.intersection(set(anidb_tags), set(current_tags)))

    updated_tags = []
    for current_tag in current_tags:
        for anidb_tag in anidb_tags:
            if (current_tag.title == anidb_tag.title
                and current_tag.weight != anidb_tag.weight):
                updated_tags.append(anidb_tag)

    return {
        'deleted_tags': deleted_tags,
        'added_tags': added_tags,
        'updated_tags': updated_tags,
        'kept_tags': kept_tags
    }

def is_nsfw_based_on_anidb_tags(anidb_tags: List[AniDBTag]) -> bool:
    # FIXME: potentially NSFW tags should be stored somewhere else
    potentially_nsfw_tags = ['nudity', 'ecchi', 'pantsu', 'breasts', 'sex',
                             'large breasts', 'small breasts', 'gigantic breasts',
                             'incest', 'pornography', 'shota', 'masturbation',
                             'sexual fantasies', 'anal', 'loli']

     # FIXME: these should be configurable constants
    HIGH_NSFW_THRESHOLD = 15
    LOW_NSFW_THRESHOLD = 30

    sum_weight_all_low = sum(tag.weight for tag in anidb_tags if tag.weight <= 400)
    sum_weight_nsfw_low = sum(tag.weight for tag in anidb_tags
                              if tag.title in potentially_nsfw_tags and tag.weight <= 400)

    sum_weight_all_high = sum(tag.weight for tag in anidb_tags if tag.weight > 400)
    sum_weight_nsfw_high = sum(tag.weight for tag in anidb_tags
                               if tag.title in potentially_nsfw_tags and tag.weight > 400)

    if sum_weight_all_low > 0 and sum_weight_all_high > 0:
        percent_low_nsfw = (sum_weight_nsfw_low/sum_weight_all_low) * 100
        percent_high_nsfw = (sum_weight_nsfw_high/sum_weight_all_high) * 100
    else:
        return False

    return (percent_high_nsfw > HIGH_NSFW_THRESHOLD or percent_low_nsfw > LOW_NSFW_THRESHOLD)
