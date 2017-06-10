# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-10 12:04
from __future__ import unicode_literals

from django.db import migrations


def add_simple(apps, _):
    Language = apps.get_model('mangaki', 'Language')

    Language.objects.create(code='simple')


def remove_simple(apps, _):
    Language = apps.get_model('mangaki', 'Language')

    Language.objects.filter(code='simple').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('mangaki', '0072_fill_ext_languages'),
    ]

    operations = [
        migrations.RunPython(add_simple, remove_simple)
    ]
