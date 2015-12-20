# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0023_auto_20151220_1706'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reference',
            name='suggestion',
        ),
        migrations.AddField(
            model_name='reference',
            name='suggestions',
            field=models.ManyToManyField(to='mangaki.Suggestion', blank=True, null=True),
            preserve_default=True,
        ),
    ]
