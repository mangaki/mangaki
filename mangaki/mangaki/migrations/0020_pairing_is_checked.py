# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0019_pairing'),
    ]

    operations = [
        migrations.AddField(
            model_name='pairing',
            name='is_checked',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
