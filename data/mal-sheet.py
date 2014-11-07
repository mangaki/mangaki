from urllib.request import urlopen
from bs4 import BeautifulSoup

b = BeautifulSoup(urlopen('http://myanimelist.net/anime/23283/Zankyou_no_Terror'))
print(b)
print(b.find('img'))
