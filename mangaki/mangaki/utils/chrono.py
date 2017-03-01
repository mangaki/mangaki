from datetime import datetime


class Chrono(object):
    checkpoint = None
    connection = None
    is_enabled = True

    def __init__(self, is_enabled, connection=None):
        self.is_enabled = is_enabled
        self.connection = connection
        self.checkpoint = datetime.now()

    def save(self, title):
        if self.is_enabled:
            now = datetime.now()
            delta = now - self.checkpoint
            if self.connection:
                print('Chrono:', title, '[%dq, %dms]' % (len(self.connection.queries), round(delta.total_seconds() * 1000)))
            self.checkpoint = now
