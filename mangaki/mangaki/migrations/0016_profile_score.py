# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0015_auto_20150626_0839'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='score',
            field=models.IntegerField(default=0),
        ),
    ]
