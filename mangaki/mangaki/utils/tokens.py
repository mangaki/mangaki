from django.utils.crypto import salted_hmac
from django.conf import settings


KYOTO_SALT = 'research-kyoto-2017'


def compute_token(salt, username):
    return salted_hmac(salt, username).hexdigest()
