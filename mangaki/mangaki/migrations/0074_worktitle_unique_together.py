# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-10 12:15
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0073_add_simple_lang'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='worktitle',
            unique_together=set([('title', 'language')]),
        ),
    ]