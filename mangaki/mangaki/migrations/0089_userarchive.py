# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-05-07 20:12
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mangaki', '0088_profile_keyboard_shortcuts_enabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserArchive',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('local_archive', models.FileField(upload_to='user_archives/')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
