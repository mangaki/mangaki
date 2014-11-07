# coding=utf8
from django.db import models
from django.contrib.auth.models import User

class Work(models.Model):
    title = models.CharField(max_length=64)
    source = models.CharField(max_length=128)
    poster = models.CharField(max_length=128)

class Anime(Work):
    synopsis = models.TextField()
    director = models.ForeignKey('Artist', related_name='directed')
    composer = models.ForeignKey('Artist', related_name='composed')
    def __str__(self):
        return self.title

class Track(models.Model):
    title = models.CharField(max_length=32)
    ost = models.ForeignKey('OST')
    def __str__(self):
        return self.title

class OST(Work):
    def __str__(self):
        return self.title

class Artist(models.Model):
    first_name = models.CharField(max_length=32)
    last_name = models.CharField(max_length=32)
    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)

class Rating(models.Model):
    user = models.ForeignKey(User)
    work = models.ForeignKey(Work)
    choice = models.CharField(max_length=7, choices=(
        ('like', 'J\'aime'),
        ('dislike', 'Je n\'aime pas'),
        ('neutral', 'Neutre'),
        ('willsee', 'Je veux voir'),
        ('wontsee', 'Je ne veux pas voir')
    ))
