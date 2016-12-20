# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mangaki', '0002_auto_20150129_0110'),
    ]

    operations = [
        migrations.CreateModel(
            name='Suggestion',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', primary_key=True, auto_created=True)),
                ('date', models.DateTimeField(auto_now=True)),
                ('problem', models.CharField(max_length=8, choices=[('title', "Le titre n'est pas le bon"), ('poster', 'Le poster ne convient pas'), ('synopsis', 'Le synopsis comporte des erreurs')], verbose_name='Problème')),
                ('message', models.TextField(blank=True, verbose_name='Correction (facultatif)')),
                ('is_checked', models.BooleanField(default=False)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
                ('work', models.ForeignKey(to='mangaki.Work', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
