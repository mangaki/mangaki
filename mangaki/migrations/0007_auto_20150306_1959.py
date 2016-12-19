# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0006_neighborship'),
    ]

    operations = [
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=17)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Manga',
            fields=[
                ('work_ptr', models.OneToOneField(parent_link=True, auto_created=True, to='mangaki.Work', primary_key=True, serialize=False, on_delete=models.CASCADE)),
                ('vo_title', models.CharField(max_length=128)),
                ('editor', models.CharField(max_length=32)),
                ('origin', models.CharField(choices=[('japon', 'Japon'), ('coree', 'Coree'), ('france', 'France'), ('chine', 'Chine'), ('usa', 'USA'), ('allemagne', 'Allemagne'), ('taiwan', 'Taiwan'), ('espagne', 'Espagne'), ('angleterre', 'Angleterre'), ('hong-kong', 'Hong Kong'), ('italie', 'Italie'), ('inconnue', 'Inconnue')], max_length=10)),
                ('manga_type', models.TextField(choices=[('seinen', 'Seinen'), ('shonen', 'Shonen'), ('shojo', 'Shojo'), ('yaoi', 'Yaoi'), ('sonyun-manhwa', 'Sonyun-Manhwa'), ('kodomo', 'Kodomo'), ('ecchi-hentai', 'Ecchi-Hentai'), ('global-manga', 'Global-Manga'), ('manhua', 'Manhua'), ('josei', 'Josei'), ('sunjung-sunjeong', 'Sunjung-Sunjeong'), ('chungnyun', 'Chungnyun'), ('yuri', 'Yuri'), ('dojinshi-parodie', 'Dojinshi-Parodie'), ('manhwa', 'Manhwa'), ('yonkoma', 'Yonkoma')], max_length=16)),
                ('genre', models.ManyToManyField(to='mangaki.Genre')),
                ('mangaka', models.ForeignKey(related_name='drew', to='mangaki.Artist', on_delete=models.CASCADE)),
                ('writer', models.ForeignKey(related_name='wrote', to='mangaki.Artist', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=('mangaki.work',),
        ),
        migrations.RemoveField(
            model_name='anime',
            name='synopsis',
        ),
        migrations.AddField(
            model_name='work',
            name='synopsis',
            field=models.TextField(default='', blank=True),
            preserve_default=True,
        ),
    ]
