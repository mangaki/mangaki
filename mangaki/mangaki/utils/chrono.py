from datetime import datetime

class Chrono(object):
    checkpoint = None
    is_enabled = True
    def __init__(self, is_enabled):
        self.is_enabled = is_enabled
        self.checkpoint = datetime.now()
    def save(self, title):
        if self.is_enabled:
            now = datetime.now()
            delta = now - self.checkpoint
            print(title, '[%d ms]' % round(delta.microseconds / 1000))
            self.checkpoint = now
