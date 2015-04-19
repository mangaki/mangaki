# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0008_auto_20150323_1842'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='avatar_url',
            field=models.CharField(blank=True, max_length=128, null=True, default=''),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='profile',
            name='mal_username',
            field=models.CharField(blank=True, max_length=64, null=True, default=''),
            preserve_default=True,
        ),
    ]
