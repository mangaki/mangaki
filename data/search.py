from urllib.request import urlopen
import sys
from bs4 import BeautifulSoup

#print(urlopen('http://www.animeka.com/search/index.html?req=%s' % sys.argv[1]).read())

b = BeautifulSoup(urlopen('http://www.animeka.com/search/index.html?req=%s' % sys.argv[1])) # &go_search=1&cat=search&zone_series=1&zone_episodes=1&zone_studios=1&zone_pers=1&zone_seriesf=1&zone_rlz=1&zone_team=1&type_search=all
results = list(b.select('.animestxt a'))
if len(results) >= 1:
    for line in results:
        print(line['href'])
else:
    js = b.find('script').text
    print(js[js.index('"') + 1:-1])
