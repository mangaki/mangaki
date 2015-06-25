# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0012_auto_20150616_0832'),
    ]

    operations = [
        migrations.AddField(
            model_name='anime',
            name='anime_type',
            field=models.TextField(max_length=42, default=''),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='anime',
            name='author',
            field=models.ForeignKey(default=1, to='mangaki.Artist', related_name='authored'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='anime',
            name='editor',
            field=models.ForeignKey(default=1, to='mangaki.Editor'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='anime',
            name='genre',
            field=models.ManyToManyField(to='mangaki.Genre'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='anime',
            name='nb_episodes',
            field=models.TextField(max_length=16, default='Inconnu'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='anime',
            name='origin',
            field=models.CharField(max_length=10, default='', choices=[('japon', 'Japon'), ('coree', 'Coree'), ('france', 'France'), ('chine', 'Chine'), ('usa', 'USA'), ('allemagne', 'Allemagne'), ('taiwan', 'Taiwan'), ('espagne', 'Espagne'), ('angleterre', 'Angleterre'), ('hong-kong', 'Hong Kong'), ('italie', 'Italie'), ('inconnue', 'Inconnue'), ('intl', 'International')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='anime',
            name='studio',
            field=models.ForeignKey(default=1, to='mangaki.Studio'),
            preserve_default=True,
        ),
    ]
