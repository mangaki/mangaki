from django.db import models
from mangaki.models import Work


class Partner(models.Model):
    name = models.CharField(max_length=32)
    url = models.CharField(max_length=512)
    image = models.CharField(max_length=32, verbose_name="Fichier logo")

    class Meta:
        ordering = ['name']
