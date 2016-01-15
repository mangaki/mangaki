from django import template

register = template.Library()

from django.conf import settings
from django.utils.safestring import mark_safe

import os
import os.path
import urllib
import json

ROOT = settings.BASE_DIR
STATIC_ASSET_PATH = os.path.join('static', 'assets')


def fetch_production_file(file_name, manifest_file):
    # 1. Read the manifest to map generic name to long term caching version
    manifest_path = os.path.join(ROOT, STATIC_ASSET_PATH, manifest_file)
    assetsMap = {}

    try:
        fp = open(manifest_path, 'r')
    except PermissionError:
        raise Exception("Cannot access to the asset manifest file {}"\
                        .format(manifest_path))
    else:
        with fp:
            assetsMap = json.loads(fp.read())

    # Get the real path to the real asset version
    real_path = assetsMap['/' + os.path.join(STATIC_ASSET_PATH, file_name)]
    if os.path.exists(os.path.join(ROOT, real_path[1:])):
        return mark_safe(real_path)
    else:
        raise Exception("File {} does not exists on the filesystem,"
                        " double-check your Webpack compilation."\
                        .format(real_path))

def webpack_server_url(file_name):
    try:
        webpack_url = settings.WEBPACK_URL or 'http://localhost:3000'
        # Check if the file exists on the server
        r = urllib.request.urlopen('{}/{}'.format(webpack_url, file_name))
    except urllib.error.HTTPError as e:
        raise Exception("File {} seems not to exists on Webpack Server"\
                            .format(file_name))
    except Exception as e:
        print (e)
    else:
        return mark_safe('{}/{}'.format(webpack_url, file_name))



@register.simple_tag(name='asset_for')
def asset_for(asset_name, manifest_file='manifest.json'):
    try:
        if settings.DEBUG: # Not production
            try:
                return webpack_server_url(asset_name)
            except:
                return fetch_production_file(asset_name, manifest_file)
        else:
            return fetch_production_file(asset_name, manifest_file)
    except Exception as e:
        if asset_name.endswith('css') and settings.DEBUG:
            return ''
        else:
            raise e
