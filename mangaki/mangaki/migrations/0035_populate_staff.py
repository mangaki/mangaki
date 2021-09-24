# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-04-09 10:34
from __future__ import unicode_literals

from django.db import migrations


def populate_staff(apps, schema_editor):
    Role = apps.get_model("mangaki", "Role")
    Staff = apps.get_model("mangaki", "Staff")
    Anime = apps.get_model("mangaki", "Anime")
    Manga = apps.get_model("mangaki", "Manga")

    anime_fields = ['director', 'composer', 'author']
    manga_fields = ['mangaka', 'writer']
    data = [(Anime, field) for field in anime_fields] + [(Manga, field) for field in manga_fields]
    for model, field in data:
        role = Role.objects.get(slug=field)
        Staff.objects.bulk_create([
            Staff(work_id=work.id, artist_id=getattr(work, field + '_id'), role=role)
            for work in model.objects.only('pk', field + '_id').all()
            if getattr(work, field + '_id') != 1
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0034_populate_stafftype'),
    ]

    operations = [
        migrations.RunPython(code=populate_staff)
    ]
