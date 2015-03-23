# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mangaki', '0007_auto_20150306_1959'),
    ]

    operations = [
        migrations.AlterField(
            model_name='artist',
            name='first_name',
            field=models.CharField(null=True, blank=True, max_length=32),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='manga',
            name='origin',
            field=models.CharField(choices=[('japon', 'Japon'), ('coree', 'Coree'), ('france', 'France'), ('chine', 'Chine'), ('usa', 'USA'), ('allemagne', 'Allemagne'), ('taiwan', 'Taiwan'), ('espagne', 'Espagne'), ('angleterre', 'Angleterre'), ('hong-kong', 'Hong Kong'), ('italie', 'Italie'), ('inconnue', 'Inconnue'), ('intl', 'International')], max_length=10),
            preserve_default=True,
        ),
    ]
