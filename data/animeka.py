from urllib.request import urlopen
from bs4 import BeautifulSoup

b = BeautifulSoup(urlopen('http://www.animeka.com/animes/detail/zankyou-no-terror.html').read())
lines = list(map(lambda x: x.text, b.select('.animesindex > tr')))
print(lines[lines.index('Synopsis') + 1])
