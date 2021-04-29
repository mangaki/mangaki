# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from django.db import models
from mangaki.models import Work
from django.contrib.auth.models import User
import locale


class Partner(models.Model):
    name = models.CharField(max_length=32)
    url = models.CharField(max_length=512)
    image = models.CharField(max_length=32, verbose_name="Fichier logo")

    class Meta:
        ordering = ['name'] 
