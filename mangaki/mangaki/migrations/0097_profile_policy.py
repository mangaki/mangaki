# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-08-11 12:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0096_auto_20180808_1538'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='policy',
            field=models.CharField(blank=True, choices=[('standard', 'Standard'), ('strict', 'Strict'), ('gentle', 'Noble')], max_length=64, null=True),
        ),
    ]
