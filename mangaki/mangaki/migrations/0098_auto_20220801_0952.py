# Generated by Django 2.2.25 on 2022-08-01 09:52

import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0097_add_friends_20211201_1616'),
    ]

    operations = [
        migrations.AddField(
            model_name='work',
            name='search_terms',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='work',
            name='titles_search',
            field=django.contrib.postgres.search.SearchVectorField(null=True),
        ),
        migrations.AlterField(
            model_name='work',
            name='ext_poster',
            field=models.CharField(db_index=True, max_length=256),
        ),
        migrations.AlterField(
            model_name='worktitle',
            name='title',
            field=models.CharField(blank=True, db_index=True, max_length=300),
        ),
        migrations.AddIndex(
            model_name='work',
            index=django.contrib.postgres.indexes.GinIndex(fields=['titles_search'], name='mangaki_wor_titles__028ab5_gin'),
        ),
    ]
