from django.core.management.base import BaseCommand, CommandError
from bs4 import BeautifulSoup
from secret import DUMMY
import requests
from datetime import datetime

DEBUG = False
DOMAIN = 'http://localhost:8000' if DEBUG else 'http://mangaki.fr'


class Report(object):
    def __init__(self, session):
        self.f = None
        self.s = session

    def __enter__(self):
        self.f = open('%s.txt' % datetime.now().isoformat(), 'w')
        return self

    def __exit__(self, type, value, traceback):
        self.f.close()

    def time_page(self, url):
        print(url)
        self.f.write(url + '\n')
        begin = datetime.now()
        self.s.get('%s%s' % (DOMAIN, url))
        self.f.write('%s\n' % (datetime.now() - begin))


class Command(BaseCommand):
    args = ''
    help = 'Time loading'

    def handle(self, *args, **options):
        begin = datetime.now()
        s = requests.session()
        r = s.get('%s/user/login/' % DOMAIN)
        b = BeautifulSoup(r.text)
        csrf = b.find('input', {'name': 'csrfmiddlewaretoken'})['value']
        print(csrf)
        s.post('%s/user/login/' % DOMAIN, {'csrfmiddlewaretoken': csrf, 'login': 'jj', 'password': DUMMY, 'remember': '1'})
        with Report(s) as report:
            report.time_page('/anime/')
            report.time_page('/user/jj/')
            report.time_page('/users/')
            report.time_page('/reco/')
            report.time_page('/data/reco/all/unspecified.json')
        # r = s.get('%s/reco/' % DOMAIN)
        # b = BeautifulSoup(r.text)
        # print(b)
