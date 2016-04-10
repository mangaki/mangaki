# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-04-10 19:02
from __future__ import unicode_literals

from django.db import migrations, models

def move_genre_to_work(apps, schema_editor):
    Work = apps.get_model("mangaki", "Work")
    Anime = apps.get_model("mangaki", "Anime")
    Manga = apps.get_model("mangaki", "Manga")

    # The genre field is now in the Work base class, while the deprecated_genre
    # is in the two derived classes and contains the value of interest.
    for anime in Anime.objects.all():
        anime.genre = anime.deprecated_genre.all()
    for manga in Manga.objects.all():
        manga.genre = manga.deprecated_genre.all()


def move_genre_from_work(apps, schema_editor):
    Work = apps.get_model("mangaki", "Work")
    Anime = apps.get_model("mangaki", "Anime")
    Manga = apps.get_model("mangaki", "Manga")

    for anime in Anime.objects.all():
        anime.deprecated_genre = anime.genre.all()
    for manga in Manga.objects.all():
        manga.deprecated_genre = manga.genre.all()


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0037_auto_20160410_1847'),
    ]

    operations = [
        migrations.RenameField(
            model_name='anime',
            old_name='genre',
            new_name='deprecated_genre',
        ),
        migrations.RenameField(
            model_name='manga',
            old_name='genre',
            new_name='deprecated_genre',
        ),
        migrations.AddField(
            model_name='work',
            name='genre',
            field=models.ManyToManyField(to='mangaki.Genre'),
        ),
        migrations.RunPython(move_genre_to_work, reverse_code=move_genre_from_work)
    ]
