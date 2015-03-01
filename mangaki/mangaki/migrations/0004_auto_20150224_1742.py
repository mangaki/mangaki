# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0003_suggestion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='work',
            name='source',
            field=models.CharField(blank=True, max_length=1044),
            preserve_default=True,
        ),
    ]
