# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0020_pairing_is_checked'),
    ]

    operations = [
        migrations.CreateModel(
            name='Deck',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(max_length=32)),
                ('sort_mode', models.CharField(max_length=32)),
                ('content', models.CommaSeparatedIntegerField(max_length=42000)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
