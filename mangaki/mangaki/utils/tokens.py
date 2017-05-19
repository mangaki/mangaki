from django.utils.crypto import salted_hmac
from django.conf import settings


def compute_token(salt, username):
    return salted_hmac(settings.HASH_NACL, username).hexdigest()
