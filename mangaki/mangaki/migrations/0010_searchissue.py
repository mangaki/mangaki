# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mangaki', '0009_auto_20150419_0758'),
    ]

    operations = [
        migrations.CreateModel(
            name='SearchIssue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('date', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=128)),
                ('poster', models.CharField(null=True, max_length=128, blank=True)),
                ('mal_id', models.IntegerField(null=True, blank=True)),
                ('score', models.IntegerField(null=True, blank=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
