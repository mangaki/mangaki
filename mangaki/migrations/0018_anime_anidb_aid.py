# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0017_profile_newsletter_ok'),
    ]

    operations = [
        migrations.AddField(
            model_name='anime',
            name='anidb_aid',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
    ]
