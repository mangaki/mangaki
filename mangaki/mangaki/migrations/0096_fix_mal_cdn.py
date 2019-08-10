# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

FORMER_CDN = 'myanimelist.cdn-dena.com'
NEW_CDN = 'cdn.myanimelist.net'


def fix_mal_cdn(apps, editor):
    Work = apps.get_model('mangaki', 'Work')
    db_alias = editor.connection.alias
    broken_works = list(Work.objects.using(db_alias)
                        .filter(ext_poster__contains=FORMER_CDN))

    for broken_work in broken_works:
        broken_work.ext_poster = broken_work.ext_poster.replace(FORMER_CDN, NEW_CDN)
        broken_work.save()


class Migration(migrations.Migration):
    dependencies = [
        ('mangaki', '0095_auto_20180826_1148'),
    ]

    operations = [
        migrations.RunPython(fix_mal_cdn)
    ]
