# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-07-13 12:12
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0079_add_tags_anidb_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='RelatedWork',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('', 'Inconnu'), ('prequel', 'Préquelle'), ('sequel', 'Suite'), ('summary', 'Résumé'), ('side_story', 'Histoire parallèle'), ('parent_story', 'Histoire mère'), ('alternative_setting', 'Univers alternatif'), ('same_setting', 'Univers commun'), ('other', 'Spécial')], default='', max_length=20, verbose_name='Type de relation')),
            ],
        ),
        migrations.AddField(
            model_name='relatedwork',
            name='child_work',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='child_work', to='mangaki.Work'),
        ),
        migrations.AddField(
            model_name='relatedwork',
            name='parent_work',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parent_work', to='mangaki.Work'),
        ),
        migrations.AlterUniqueTogether(
            name='relatedwork',
            unique_together=set([('parent_work', 'child_work', 'type')]),
        ),
    ]
