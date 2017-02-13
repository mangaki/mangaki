import html
import re
import xml.etree.ElementTree as ET

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from mangaki.models import Work


def poster(query):
    xml = re.sub(r'&([^alg])', r'&amp;\1', html.unescape(re.sub(r'&amp;([A-Za-z]+);', r'&\1;', requests.get('http://myanimelist.net/api/anime/search.xml', params={'q': query}, headers={'X-Real-IP': '251.223.201.178', 'User-Agent': 'Mozilla/5.0 (X11; Linux i686 on x86_64; rv:36.0) Gecko/20100101 Firefox/36.0'}, auth=(settings.MAL_USER, settings.MAL_PASS)).text).replace('&lt', '&lot;').replace('&gt;', '&got;')).replace('&lot;', '&lt').replace('&got;', '&gt;'))
    return ET.fromstring(xml).find('entry').find('image').text


class Command(BaseCommand):
    args = ''
    help = 'Fetches anime posters'

    def handle(self, *args, **options):
        for anime in Work.objects.filter(category__slug='anime', ext_poster=''):
            try:
                anime.ext_poster = poster(anime.title)
                anime.save()
                print('Done', anime.title)
            except:
                print('Error', anime.title)
