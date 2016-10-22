"""
This module contains multiple functions to scrap MyAnimeList,
looking for anime and finding URL of posters.
"""

import xml.etree.ElementTree as ET
import requests
import html
import re
from functools import reduce
from random import randint

from django.conf import settings

from django.contrib.auth.models import User
from mangaki.models import Work, Rating, SearchIssue, Artist, Category


def _encoding_translation(text):
    translations = {
        '&lt': '&lot;',
        '&gt;': '&got;',
        '&lot;': '&lt',
        '&got;': '&gt;'
    }

    return reduce(lambda s, r: s.replace(*r), translations.items(), text)


def random_ip():
    return '.'.join(map(str, [randint(100, 255) for _ in range(4)]))


def retrieve_anime(entries):
    unknown = Artist.objects.get(id=1)
    anime_cat = Category.objects.get(slug='anime')
    for entry in entries:
        if Work.objects.filter(category=anime_cat, poster=entry['image']).count() == 0:  # SCANDALE
            title = entry['english'] if entry['english'] else entry['title']
            if '0000' in entry['start_date']:
                anime_date = None
            elif '-00-00' in entry['start_date']:
                anime_date = entry['start_date'].replace('-00-00', '-01-01')
            elif '-00' in entry['start_date']:
                anime_date = entry['start_date'].replace('-00', '-01')
            else:
                anime_date = entry['start_date']
            Work.objects.create(category=anime_cat, title=title, source='http://myanimelist.net/anime/' + entry['id'], poster=entry['image'], date=anime_date)


def lookup_mal_api(query):
    """
    Run a query on MyAnimeList using its XML search API.
    """

    SEARCH_URL = 'http://myanimelist.net/api/anime/search.xml'
    HEADERS = {
        'X-Real-IP': random_ip(),
        'User-Agent': settings.MAL_USER_AGENT
    }

    r = requests.get(SEARCH_URL, params={'q': query}, headers=HEADERS,
                     auth=(settings.MAL_USER, settings.MAL_PASS))
    html_code = html.unescape(re.sub(r'&amp;([A-Za-z]+);', r'&\1;', r.text))
    xml = re.sub(r'&([^alg])', r'&amp;\1', _encoding_translation(html_code))

    entries = []
    try:
        for entry in ET.fromstring(xml).findall('entry'):
            data = {}
            for child in entry:
                data[child.tag] = child.text
            entries.append(data)
    except ET.ParseError:
        print(HEADERS)
        pass

    return entries


def poster_url(query):
    """
    Look for an anime on MyAnimeList and return the URL of its poster.
    """

    SEARCH_URL = 'http://myanimelist.net/api/anime/search.xml'
    HEADERS = {
        'X-Real-IP': random_ip(),
        'User-Agent': 'Mozilla/5.0 (X11; Linux i686 on x86_64; rv:36.0) Gecko/20100101 Firefox/36.0'
    }

    r = requests.get(SEARCH_URL,
                     params={'q': query},
                     headers=HEADERS,
                     auth=(settings.MAL_USER, settings.MAL_PASS))

    html_code = html.unescape(re.sub(r'&amp;([A-Za-z]+);', r'&\1;', r.text))
    xml = re.sub(r'&([^alg])', r'&amp;\1', _encoding_translation(html_code))
    return ET.fromstring(xml).find('entry').find('image').text


def import_mal(mal_username, mangaki_username):
    """
    Import myAnimeList by username
    """

    MAL_URL = 'http://myanimelist.net/malappinfo.php?u=%s&status=all&type=anime' % mal_username
    HEADERS = {
        'X-Real-IP': random_ip(),
        'User-Agent': settings.MAL_USER_AGENT
    }
    r = requests.get(MAL_URL, headers=HEADERS)
    xml = ET.fromstring(r.text)
    user = User.objects.get(username=mangaki_username)
    nb_added = 0
    fails = []
    for entry in xml:
        if entry.tag == 'anime':
            title = entry.find('series_title').text
            poster = entry.find('series_image').text
            score = int(entry.find('my_score').text)
            mal_id = entry.find('series_animedb_id').text
            try:
                animes = Work.objects.filter(category__slug='anime')
                try:
                    anime = animes.get(title=title)
                except Work.DoesNotExist:
                    if animes.filter(poster=poster).count() == 1:
                        anime = Work.objects.get(poster=poster)
                    elif animes.filter(poster=poster).count() >= 2:
                        raise Exception('Integrity violation: found two or more works with the same poster, do you come from the past?')
                    else:
                        entries = lookup_mal_api(title)
                        retrieve_anime(entries)
                        anime = animes.get(poster=poster)
                if anime:
                    if not Rating.objects.filter(user=user, work=anime).count():
                        if 7 <= score <= 10:
                            choice = 'like'
                        elif 5 <= score <= 6:
                            choice = 'neutral'
                        elif score > 0:
                            choice = 'dislike'
                        else:
                            continue
                        Rating(user=user, work=anime, choice=choice).save()
                        nb_added += 1
            except Exception as e:
                print(e)
                SearchIssue(user=user, title=title, poster=poster, mal_id=mal_id, score=score).save()
                fails.append(title)
    return nb_added, fails

class MAL:
    def __init__(self):
        self.SEARCH_URL = 'http://myanimelist.net/api/anime/search.xml'
        self.HEADERS = {
            'X-Real-IP': random_ip(),
            'User-Agent': 'Mozilla/5.0 (X11; Linux i686 on x86_64; rv:36.0) Gecko/20100101 Firefox/36.0'
        }
        self.entry = None

    def search(self, query):
        r = requests.get(self.SEARCH_URL,
            params={'q': query},
            headers=self.HEADERS,
            auth=(settings.MAL_USER, settings.MAL_PASS))
        html_code = html.unescape(re.sub(r'&amp;([A-Za-z]+);', r'&\1;', r.text))
        xml = re.sub(r'&([^alg])', r'&amp;\1', _encoding_translation(html_code))
        try:
            self.entry = ET.fromstring(xml).find('entry')
        except ET.ParseError as e:
            print(e)

    def get_poster(self):
        if self.entry:
            return self.entry.find('image').text
        else:
            return ''
