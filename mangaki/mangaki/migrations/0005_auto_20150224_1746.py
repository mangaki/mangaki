# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0004_auto_20150224_1742'),
    ]

    operations = [
        migrations.AlterField(
            model_name='work',
            name='title',
            field=models.CharField(max_length=128),
            preserve_default=True,
        ),
    ]
