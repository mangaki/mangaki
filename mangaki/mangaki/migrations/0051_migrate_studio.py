# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-04-10 21:00
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0050_auto_20160410_2048'),
    ]

    operations = [
        migrations.RenameField(
            model_name='anime',
            old_name='studio',
            new_name='deprecated_studio',
        ),
        migrations.AddField(
            model_name='work',
            name='studio',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='mangaki.Studio'),
        ),
    ]
