# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0010_searchissue'),
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('title', models.CharField(max_length=128)),
                ('text', models.CharField(max_length=512)),
            ],
        ),
        migrations.AlterField(
            model_name='suggestion',
            name='message',
            field=models.TextField(blank=True, verbose_name='Proposition'),
        ),
        migrations.AlterField(
            model_name='suggestion',
            name='problem',
            field=models.CharField(max_length=8, choices=[('title', "Le titre n'est pas le bon"), ('poster', 'Le poster ne convient pas'), ('synopsis', 'Le synopsis comporte des erreurs'), ('author', "L'auteur n'est pas le bon"), ('compositor', "Le compositeur n'est pas le bon"), ('double', 'Ceci est un doublon'), ('nsfw', "L'oeuvre est NSFW"), ('n_nsfw', "L'oeuvre n'est pas NSFW"), ('empty', 'La page est vide')], verbose_name='Partie concernée'),
        ),
    ]
