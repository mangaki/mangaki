from pydiscourse.client import DiscourseClient
from django.conf import settings
import datetime

def get_discourse_data(email):
    if settings.HAS_DISCOURSE:
        client = DiscourseClient('http://meta.mangaki.fr', api_username=settings.DISCOURSE_API_USERNAME, api_key=settings.DISCOURSE_API_KEY)
        try:
            users = client._get('/admin/users/list/active.json?show_emails=true')
            for user in users:
                if user['email'] == email:
                    return {'avatar': 'http://meta.mangaki.fr' + user['avatar_template'], 'created_at': user['created_at']}
        except:
            pass

    return {
        'avatar': '/static/img/unknown.png',
        'created_at': datetime.datetime.now().isoformat() + 'Z'
    }
