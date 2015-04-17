"""
This module contains multiple functions to scrap MyAnimeList,
looking for anime and finding posters' URL.
"""

import xml.etree.ElementTree as ET
import requests
import html
import re

from secret import MAL_USER, MAL_PASS


def _encoding_translation(text):
    translations = {
        '&lt': '&lot;',
        '&gt;': '&got;',
        '&lot;': '&lt',
        '&got;': '&gt;'
    }

    return reduce(lambda s, r: s.replace(*r), translations.items(), text)


def lookup_mal_api(query):
    """
    Run a query on MyAnimeList using its XML search API.
    """

    SEARCH_URL = 'http://myanimelist.net/api/anime/search.xml'
    HEADERS = {
        'X-Real-IP': '251.223.201.179',
        'User-Agent': 'Mozilla/5.0 (X11; Linux i686 on x86_64; rv:36.0) Gecko/20100101 Firefox/36.0'
    }

    r = requests.get(SEARCH_URL, params={'q': query}, headers=HEADERS,
                     auth=(MAL_USER, MAL_PASS))
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
        pass

    return entries


def poster_url(query):
    """
    Look for an anime on MyAnimeList and return the URL of its poster.
    """

    SEARCH_URL = 'http://myanimelist.net/api/anime/search.xml'
    HEADERS = {
        'X-Real-IP': '251.223.201.178',
        'User-Agent': 'Mozilla/5.0 (X11; Linux i686 on x86_64; rv:36.0) Gecko/20100101 Firefox/36.0'
    }

    r = requests.get(SEARCH_URL,
                     params={'q': query},
                     headers=HEADERS,
                     auth=(MAL_USER, MAL_PASS))

    html_code = html.unescape(re.sub(r'&amp;([A-Za-z]+);', r'&\1;', r.text))
    xml = re.sub(r'&([^alg])', r'&amp;\1', _encoding_translation(html_code))
    return ET.fromstring(xml).find('entry').find('image').text