# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0013_auto_20150616_0919'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='nsfw_ok',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='manga',
            name='manga_type',
            field=models.TextField(blank=True, max_length=16, choices=[('seinen', 'Seinen'), ('shonen', 'Shonen'), ('shojo', 'Shojo'), ('yaoi', 'Yaoi'), ('sonyun-manhwa', 'Sonyun-Manhwa'), ('kodomo', 'Kodomo'), ('ecchi-hentai', 'Ecchi-Hentai'), ('global-manga', 'Global-Manga'), ('manhua', 'Manhua'), ('josei', 'Josei'), ('sunjung-sunjeong', 'Sunjung-Sunjeong'), ('chungnyun', 'Chungnyun'), ('yuri', 'Yuri'), ('dojinshi-parodie', 'Dojinshi-Parodie'), ('manhwa', 'Manhwa'), ('yonkoma', 'Yonkoma')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='rating',
            name='choice',
            field=models.CharField(max_length=8, choices=[('favorite', 'Mon favori !'), ('like', "J'aime"), ('dislike', "Je n'aime pas"), ('neutral', 'Neutre'), ('willsee', 'Je veux voir'), ('wontsee', 'Je ne veux pas voir')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='suggestion',
            name='problem',
            field=models.CharField(verbose_name='Partie concernée', max_length=8, choices=[('title', "Le titre n'est pas le bon"), ('poster', 'Le poster ne convient pas'), ('synopsis', 'Le synopsis comporte des erreurs'), ('author', "L'auteur n'est pas le bon"), ('composer', "Le compositeur n'est pas le bon"), ('double', 'Ceci est un doublon'), ('nsfw', "L'oeuvre est NSFW"), ('n_nsfw', "L'oeuvre n'est pas NSFW")]),
            preserve_default=True,
        ),
    ]
