# coding=utf8
from django.db import models
from django.contrib.auth.models import User
from mangaki.api import get_discourse_data
from mangaki.choices import ORIGIN_CHOICES, TYPE_CHOICES

class Work(models.Model):
    title = models.CharField(max_length=128)
    source = models.CharField(max_length=1044, blank=True)
    poster = models.CharField(max_length=128)
    nsfw = models.BooleanField(default=False)
    date = models.DateField(blank=True, null=True)
    synopsis = models.TextField(blank=True, default='')
    def __str__(self):
        return self.title

class Anime(Work):
    director = models.ForeignKey('Artist', related_name='directed')
    composer = models.ForeignKey('Artist', related_name='composed')
    # editor
    # category
    # genre1
    # nb_tomes
    def __str__(self):
        return self.title

class Manga(Work):
    vo_title = models.CharField(max_length=128)
    mangaka = models.ForeignKey('Artist', related_name='drew')
    writer = models.ForeignKey('Artist', related_name='wrote')
    editor = models.CharField(max_length=32)
    origin = models.CharField(max_length=10, choices=ORIGIN_CHOICES)
    genre = models.ManyToManyField('Genre')
    manga_type = models.TextField(max_length=16, choices=TYPE_CHOICES)

class Genre(models.Model):
    title = models.CharField(max_length=17)
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
    first_name = models.CharField(max_length=32, blank=True, null=True)
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
    def __str__(self):
        return '%s %s %s' % (self.user, self.choice, self.work)

class Page(models.Model):
    name = models.SlugField()
    markdown = models.TextField()
    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField(User)
    is_shared = models.BooleanField(default=True)
    def anime_count(self):
        return Rating.objects.filter(user=self.user, choice__in=['like', 'neutral', 'dislike']).count()
    def avatar_url(self):
        return get_discourse_data(self.user.email)['avatar'].format(size=150)

class Suggestion(models.Model):
    user = models.ForeignKey(User)
    work = models.ForeignKey(Work)
    date = models.DateTimeField(auto_now=True)
    problem = models.CharField(verbose_name='Problème', max_length=8, choices=(
        ('title', 'Le titre n\'est pas le bon'),
        ('poster', 'Le poster ne convient pas'),
        ('synopsis', 'Le synopsis comporte des erreurs')
    ))
    message = models.TextField(verbose_name='Correction (facultatif)', blank=True)
    is_checked = models.BooleanField(default=False)

class Neighborship(models.Model):
    user = models.ForeignKey(User)
    neighbor = models.ForeignKey(User, related_name='neighbor')
    score = models.DecimalField(decimal_places=3, max_digits=8)
