# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Artist',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('first_name', models.CharField(max_length=32)),
                ('last_name', models.CharField(max_length=32)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Page',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('name', models.SlugField()),
                ('markdown', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('is_shared', models.BooleanField(default=True)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('choice', models.CharField(choices=[('like', "J'aime"), ('dislike', "Je n'aime pas"), ('neutral', 'Neutre'), ('willsee', 'Je veux voir'), ('wontsee', 'Je ne veux pas voir')], max_length=7)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Track',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('title', models.CharField(max_length=32)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Work',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('title', models.CharField(max_length=64)),
                ('source', models.CharField(blank=True, max_length=128)),
                ('poster', models.CharField(max_length=128)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OST',
            fields=[
                ('work_ptr', models.OneToOneField(serialize=False, to='mangaki.Work', primary_key=True, parent_link=True, auto_created=True, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=('mangaki.work',),
        ),
        migrations.CreateModel(
            name='Anime',
            fields=[
                ('work_ptr', models.OneToOneField(serialize=False, to='mangaki.Work', primary_key=True, parent_link=True, auto_created=True, on_delete=models.CASCADE)),
                ('synopsis', models.TextField(blank=True)),
                ('composer', models.ForeignKey(to='mangaki.Artist', related_name='composed', on_delete=models.CASCADE)),
                ('director', models.ForeignKey(to='mangaki.Artist', related_name='directed', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=('mangaki.work',),
        ),
        migrations.AddField(
            model_name='track',
            name='ost',
            field=models.ForeignKey(to='mangaki.OST', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rating',
            name='work',
            field=models.ForeignKey(to='mangaki.Work', on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
