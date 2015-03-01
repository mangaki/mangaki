# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mangaki', '0005_auto_20150224_1746'),
    ]

    operations = [
        migrations.CreateModel(
            name='Neighborship',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('score', models.DecimalField(decimal_places=3, max_digits=8)),
                ('neighbor', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='neighbor')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
