import base64
import hmac
import hashlib
from urllib.parse import unquote, parse_qs, urlencode

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.conf import settings


@login_required
def sso(request):
    payload = request.GET.get('sso')
    signature = request.GET.get('sig')

    if None in [payload, signature]:
        return HttpResponseBadRequest('No SSO payload or signature. Please contact support if this problem persists.')

    # Validate the payload

    try:
        payload = unquote(payload)
        decoded = base64.decodestring(bytes(payload, 'utf-8'))
        assert 'nonce' in str(decoded)
        assert len(payload) > 0
    except AssertionError:
        return HttpResponseBadRequest('Invalid payload. Please contact support if this problem persists.')

    key = str(settings.DISCOURSE_SSO_SECRET)
    h = hmac.new(key.encode('utf-8'), payload.encode('utf-8'), digestmod=hashlib.sha256)
    this_signature = h.hexdigest()

    if this_signature != signature:
        return HttpResponseBadRequest('Invalid payload. Please contact support if this problem persists.')

    # Build the return payload

    qs = parse_qs(decoded)
    params = {
        'nonce': qs[b'nonce'][0],
        'email': request.user.email,
        'external_id': request.user.id,
        'username': request.user.username,
    }

    return_payload = base64.encodestring(bytes(urlencode(params), 'utf-8'))
    h = hmac.new(key.encode('utf-8'), return_payload, digestmod=hashlib.sha256)
    query_string = urlencode({'sso': return_payload, 'sig': h.hexdigest()})

    # Redirect back to Discourse

    url = '%s/session/sso_login' % settings.DISCOURSE_BASE_URL
    return HttpResponseRedirect('%s?%s' % (url, query_string))
