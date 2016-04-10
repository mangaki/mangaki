# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-04-10 19:51
from __future__ import unicode_literals

from django.db import migrations, models

def move_anime_type_to_work(apps, schema_editor):
    Anime = apps.get_model("mangaki", "Anime")

    # The anime_type field is now in the Work base class, while the deprecated_anime_type
    # is in the two derived classes and contains the value of interest.
    for anime in Anime.objects.all():
        anime.anime_type = anime.deprecated_anime_type
        anime.save()

def move_anime_type_from_work(apps, schema_editor):
    Anime = apps.get_model("mangaki", "Anime")

    for anime in Anime.objects.all():
        anime.deprecated_anime_type = anime.anime_type
        anime.save()

class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0040_auto_20160410_1946'),
    ]

    operations = [
        migrations.RenameField(
            model_name='anime',
            old_name='anime_type',
            new_name='deprecated_anime_type',
        ),
        migrations.AddField(
            model_name='work',
            name='anime_type',
            field=models.TextField(default='', max_length=42),
        ),
        migrations.RunPython(move_anime_type_to_work, reverse_code=move_anime_type_from_work),
    ]
