from urllib.request import urlopen
from bs4 import BeautifulSoup
from slugify import slugify
import json


def link(slug):
    b = BeautifulSoup(urlopen('http://www.animeka.com/search/index.html?req=%s' % slug))  # &go_search=1&cat=search&zone_series=1&zone_episodes=1&zone_studios=1&zone_pers=1&zone_seriesf=1&zone_rlz=1&zone_team=1&type_search=all
    results = list(b.select('.animestxt a'))
    try:
        if len(results) >= 1:
            lines = []
            for line in results:
                if line['href'].startswith('/animes/detail'):
                    lines.append(line['href'].replace('/animes/detail', ''))
            return ','.join(lines)
        else:
            js = b.find('script').text
            return js[js.index('"') + 1:-1]
    except BaseException:
        return ''


def synopsis(url):
    try:
        b = BeautifulSoup(urlopen('http://www.animeka.com/animes/detail%s' % url).read())
        lines = list(map(lambda x: x.text, b.select('.animesindex tr')))
        return lines[lines.index('Synopsis') + 1]
    except BaseException:
        return ''


data = []
pk = 31
with open('anime.txt') as f:
    for line in f:
        title = line.strip()
        slug = slugify(title).replace('-', '+')
        url = link(slug)
        data.append({
            'pk': pk,
            'model': 'mangaki.work',
            'fields': {
                'title': title,
                'poster': '',
                'source': url
            },
        })
        data.append({
            'pk': pk,
            'model': 'mangaki.anime',
            'fields': {
                'synopsis': synopsis(url.split(',')[0]),
                'director': 1,
                'composer': 1
            }
        })
        pk += 1

with open('bundle.json', 'w') as f:
    f.write(json.dumps(data, indent=4))
