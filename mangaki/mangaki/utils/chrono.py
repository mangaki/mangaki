from datetime import datetime
from django.db import connection


class Chrono(object):
    checkpoint = None
    connection = None
    is_enabled = True

    def __init__(self, is_enabled, connection=None):
        self.is_enabled = is_enabled
        self.checkpoint = datetime.now()

    def save(self, title):
        if self.is_enabled:
            now = datetime.now()
            delta = now - self.checkpoint
            print('Chrono:', title, '[%dq, %dms]' % (len(connection.queries), round(delta.total_seconds() * 1000)))
            self.checkpoint = now
