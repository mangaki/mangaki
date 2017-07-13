from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.utils.functional import cached_property
from django.db.models import Q

from mangaki import settings
from mangaki.models import Work, WorkTitle, Category, ExtLanguage, Role, Staff, Studio, Artist, Tag, TaggedWork, RelatedWork


def to_python_datetime(mal_date):
    """
    Converts myAnimeList's XML date YYYY-MM-DD to Python datetime format.
    >>> to_python_datetime('2015-07-14')
    datetime.datetime(2015, 7, 14, 0, 0)
    """
    date = list(map(int, mal_date.split("-")))
    date += [1 for _ in range(3-len(date))]
    return datetime(*date)


class AniDB:
    BASE_URL = "http://api.anidb.net:9001/httpapi"
    SEARCH_URL = "http://anisearch.outrance.pl/"
    PROTOCOL_VERSION = 1

    def __init__(self,
                 client_id: Optional[str] = None,
                 client_ver: Optional[int] = None):
        if not client_id and client_ver:
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
        ext_langs = (
            ExtLanguage.objects.filter(source='anidb')
            .select_related('lang')
        )

        return {
            ext.lang.code: ext for ext in ext_langs
        }

    @cached_property
    def unknown_language(self) -> ExtLanguage:
        return ExtLanguage.objects.get(source='anidb', ext_lang='x-unk')

    def _build_work_titles(self,
                           work: Work,
                           titles: Dict[str, Dict[str, str]],
                           reload_lang_cache: bool = False) -> List[WorkTitle]:
        if reload_lang_cache:
            # noinspection PyPropertyAccess
            del self.lang_map

        work_titles = []
        raw_titles = []
        for lang, title_data in titles.items():
            ext_lang_model = self.lang_map.get(lang, self.unknown_language)
            raw_titles.append(title_data['title'])
            work_titles.append(
                WorkTitle(
                    work=work,
                    title=title_data['title'],
                    ext_language=ext_lang_model,
                    language=ext_lang_model.lang if ext_lang_model else None,
                    type=title_data['type']
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

    def get_xml(self, anidb_aid: int):
        anidb_aid = int(anidb_aid)

        r = self._request("anime", {'aid': anidb_aid})
        soup = BeautifulSoup(r.text.encode('utf-8'), 'xml')
        if soup.error is not None:
            raise Exception(soup.error.string)

        return soup.anime

    def handle_tags(self, anidb_aid=None, tags_soup=None):
        if anidb_aid is not None:
            anime = self.get_xml(anidb_aid)
            tags_soup = anime.tags

        tags = {}
        if tags_soup is not None:
            for tag_node in tags_soup.find_all('tag'):
                tag_title = str(tag_node.find('name').string).strip()
                tag_id = int(tag_node.get('id'))
                tag_weight = int(tag_node.get('weight'))
                tag_verified = tag_node.get('verified').lower() == 'true'

                if tag_verified:
                    tags[tag_title] = {"weight": tag_weight, "anidb_tag_id": tag_id}

        return tags

    def get_related_animes(self, anidb_aid=None, related_animes_soup=None):
        if anidb_aid is not None:
            anime = self.get_xml(anidb_aid)
            related_animes_soup = anime.relatedanime

        related_animes = {}
        if related_animes_soup is not None:
            for related_node in related_animes_soup.find_all('anime'):
                related_anidb_id = int(related_node.get('id'))
                related_type = str(related_node.get('type')).strip()
                related_type = related_type.lower().replace(" ", "_")

                related_animes[related_anidb_id] = related_type

        return related_animes

    def _build_related_animes(self,
                              work: Work,
                              related_animes: Dict[int, str]) -> List[RelatedWork]:
        anidb_aids = related_animes.keys()
        types = related_animes.values()

        # Retrieve missing works
        existing_works = Work.objects.filter(anidb_aid__in=anidb_aids)
        existing_anidb_aids = existing_works.values_list('anidb_aid', flat=True)
        works = [work for work in existing_works]
        for anidb_aid in anidb_aids:
            if anidb_aid not in existing_anidb_aids:
                # FIXME: Should be careful, this might spam AniDB
                works.append(self.get_or_update_work(anidb_aid=anidb_aid))

        # And create appropriate relations in the database
        # Should skip already existing relations (next commit)
        new_relations = []
        for child_work in works:
            new_relations.append(
                RelatedWork(
                    parent_work=work,
                    child_work=child_work,
                    type=related_animes[child_work.anidb_aid]
                )
            )

        RelatedWork.objects.bulk_create(new_relations)

        return new_relations

    def get_or_update_work(self,
                           anidb_aid: int,
                           reload_lang_cache: bool = False) -> Work:
        """
        Use `get_dict` internally to create (in the database) the bunch of objects you need to create a work.

        Cache internally intermediate models objects (e.g. Language, ExtLanguage, Category)

        This won't return already existing WorkTitle attached to the Work object.

        :param anidb_aid: the AniDB identifier
        :type anidb_aid: integer
        :param reload_lang_cache: forcefully reload the ExtLanguage cache,
            if it has changed since the instantiation of the AniDB client (default: false).
        :type reload_lang_cache: boolean
        :return: the Work object related to the AniDB ID passed in parameter.
        :rtype: a `mangaki.models.Work` object.
        """

        anime = self.get_xml(anidb_aid)

        anime_restricted = anime.get('restricted') == 'true'
        all_titles = anime.titles
        all_creators = anime.creators
        all_tags = anime.tags
        all_related_animes = anime.relatedanime

        # Handling of titles
        main_title = None
        synonyms = {}
        titles = {}
        for title_node in all_titles.find_all('title'):
            title = str(title_node.string).strip()
            lang = title_node.get('xml:lang')
            title_type = title_node.get('type')
            titles[lang] = {
                'title': title,
                'type': title_type
            }

            if title_type == 'main':
                main_title = title

            if title_type == 'synonym':
                synonyms[lang] = title

        # Handling of staff
        creators = []
        studio = None
        # FIXME: cache this query
        staff_map = dict(Role.objects.values_list('slug', 'pk'))
        for creator_node in all_creators.find_all('name'):
            creator = str(creator_node.string).strip()
            creator_id = creator_node.get('id')
            creator_type = creator_node.get('type')
            staff_id = None

            if creator_type == 'Direction':
                staff_id = 'director'
            elif creator_type == 'Music':
                staff_id = 'composer'
            elif creator_type == 'Original Work' or creator_type == 'Story Composition':
                staff_id = 'author'
            elif creator_type == 'Animation Work' or creator_type == 'Work':
                # AniDB marks Studio as such a creator's type
                studio, s_created = Studio.objects.get_or_create(title=creator)

            if staff_id is not None:
                creators.append({
                    "role_id": staff_map[staff_id],
                    "name": creator,
                    "anidb_creator_id": creator_id
                })

        anime = {
            'title': main_title,
            'source': 'AniDB: ' + str(anime.url.string) if anime.url else '',
            'ext_poster': urljoin('http://img7.anidb.net/pics/anime/', str(anime.picture.string)) if anime.picture else '',
            'nsfw': anime_restricted,
            'date': to_python_datetime(anime.startdate.string),
            'end_date': to_python_datetime(anime.enddate.string),
            'ext_synopsis': str(anime.description.string) if anime.description else '',
            'nb_episodes': int(anime.episodecount.string) if anime.episodecount else 0,
            'anime_type': str(anime.type.string) if anime.type else '',
            'anidb_aid': anidb_aid
        }
        if studio is not None:
            anime['studio'] = studio

        # Add or update work
        work, created = Work.objects.update_or_create(category=self.anime_category,
                                                      anidb_aid=anidb_aid,
                                                      defaults=anime)

        # Add new creators
        for nc in creators:
            artist = Artist.objects.filter(Q(name=nc["name"]) | Q(anidb_creator_id=nc["anidb_creator_id"])).first()

            if not artist: # This artist does not yet exist
                artist, a_created = Artist.objects.get_or_create(name=nc["name"], anidb_creator_id=nc["anidb_creator_id"])
            else: # This artist exists : prevent duplicates by updating with the AniDB id
                artist.name = nc["name"]
                artist.anidb_creator_id = nc["anidb_creator_id"]
                artist.save()

            Staff.objects.update_or_create(work=work, role_id=nc["role_id"], artist=artist)

        tags = self.handle_tags(tags_soup=all_tags)
        work.update_tags(tags)

        # Check for NSFW based on tags if this work is new
        if created and work.is_nsfw_based_on_tags(tags):
            work.nsfw = True
            work.save()

        related_animes = self.get_related_animes(related_animes_soup=all_related_animes)

        self._build_work_titles(work, titles, reload_lang_cache)
        self._build_related_animes(work, related_animes)

        return work

client = AniDB(
    getattr(settings, 'ANIDB_CLIENT', None),
    getattr(settings, 'ANIDB_VERSION', None))
