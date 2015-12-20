# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0021_deck'),
    ]

    operations = [
        migrations.CreateModel(
            name='Reference',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('url', models.CharField(max_length=512)),
                ('suggestion', models.ForeignKey(blank=True, to='mangaki.Suggestion', null=True)),
                ('work', models.ForeignKey(to='mangaki.Work')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
