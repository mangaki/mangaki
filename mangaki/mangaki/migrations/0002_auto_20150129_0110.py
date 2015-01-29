# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='work',
            name='date',
            field=models.DateField(blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='work',
            name='nsfw',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
