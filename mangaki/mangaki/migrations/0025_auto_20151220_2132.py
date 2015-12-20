# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0024_auto_20151220_1731'),
    ]

    operations = [
        migrations.AlterField(
            model_name='suggestion',
            name='problem',
            field=models.CharField(default='ref', max_length=8, choices=[('title', "Le titre n'est pas le bon"), ('poster', 'Le poster ne convient pas'), ('synopsis', 'Le synopsis comporte des erreurs'), ('author', "L'auteur n'est pas le bon"), ('composer', "Le compositeur n'est pas le bon"), ('double', 'Ceci est un doublon'), ('nsfw', "L'oeuvre est NSFW"), ('n_nsfw', "L'oeuvre n'est pas NSFW"), ('ref', 'Proposer une URL (myAnimeList, AniDB, Icotaku, VGMdb, etc.)')], verbose_name='Partie concernée'),
            preserve_default=True,
        ),
    ]
