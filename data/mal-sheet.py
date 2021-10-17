# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from urllib.request import urlopen
from bs4 import BeautifulSoup

b = BeautifulSoup(urlopen('http://myanimelist.net/anime/23283/Zankyou_no_Terror'))
print(b)
print(b.find('img'))
