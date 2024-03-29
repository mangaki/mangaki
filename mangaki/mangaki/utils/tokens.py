# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from django.utils.crypto import salted_hmac
from django.conf import settings


KYOTO_SALT = 'research-kyoto-2017'  # For the mailing in May regarding the data challenge with Kyoto University
NEWS_SALT = 'news'


def compute_token(salt, username):
    return salted_hmac(salt, username).hexdigest()
