# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mangaki', '0014_auto_20150624_0003'),
    ]

    operations = [
        migrations.CreateModel(
            name='Recommendation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('target_user', models.ForeignKey(related_name='target_user', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('work', models.ForeignKey(to='mangaki.Work')),
            ],
        ),
        migrations.AddField(
            model_name='profile',
            name='reco_willsee_ok',
            field=models.BooleanField(default=False),
        ),
    ]
