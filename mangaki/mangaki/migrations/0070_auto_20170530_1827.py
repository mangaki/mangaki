# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-30 18:27
from __future__ import unicode_literals

from django.db import migrations
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0069_auto_20170509_1336'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='work',
            managers=[
                ('all_objects', django.db.models.manager.Manager()),
            ],
        ),
    ]
