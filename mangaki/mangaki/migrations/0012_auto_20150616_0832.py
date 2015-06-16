# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0011_auto_20150612_1259'),
    ]

    operations = [
        migrations.CreateModel(
            name='Editor',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('title', models.CharField(max_length=33)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Studio',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('title', models.CharField(max_length=35)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='anime',
            name='composer',
            field=models.ForeignKey(to='mangaki.Artist', default=1, related_name='composed'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='anime',
            name='director',
            field=models.ForeignKey(to='mangaki.Artist', default=1, related_name='directed'),
            preserve_default=True,
        ),
    ]
