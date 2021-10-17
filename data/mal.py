# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from bs4 import BeautifulSoup

# print(urlopen('http://myanimelist.net/topanime.php?type=bypopularity').read())

b = BeautifulSoup(open('top.html').read()) # urllib2.urlopen('http://myanimelist.net/topanime.php?type=bypopularity')
for line in b.select('#content div table tr'):
    tds = line.findAll('td')
    print(tds[2].a.text)
