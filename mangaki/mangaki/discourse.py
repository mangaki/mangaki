from pydiscourse.client import DiscourseClient
from mangaki.settings.secret import DISCOURSE_API_USERNAME, DISCOURSE_API_KEY
import datetime

def get_discourse_data(email):
    client = DiscourseClient('http://meta.mangaki.fr', api_username=DISCOURSE_API_USERNAME, api_key=DISCOURSE_API_KEY)
    try:
        users = client._get('/admin/users/list/active.json?show_emails=true')
        for user in users:
            if user['email'] == email:
                return {'avatar': 'http://meta.mangaki.fr' + user['avatar_template'], 'created_at': user['created_at']}
        return {'avatar': '/static/img/unknown.png', 'created_at': datetime.datetime.now().isoformat() + 'Z'}
    except:
        return {'avatar': '/static/img/unknown.png', 'created_at': datetime.datetime.now().isoformat() + 'Z'}


