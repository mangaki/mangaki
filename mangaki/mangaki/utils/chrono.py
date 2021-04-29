# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from datetime import datetime
from django.db import connection
import logging


class Chrono(object):
    checkpoint = None
    connection = None
    is_enabled = True

    def __init__(self, is_enabled):
        self.is_enabled = is_enabled
        self.checkpoint = datetime.now()

    def save(self, title):
        if self.is_enabled:
            now = datetime.now()
            delta = now - self.checkpoint
            logging.info('Chrono: %s [%dq, %dms]', title, len(connection.queries), round(delta.total_seconds() * 1000))
            self.checkpoint = now
