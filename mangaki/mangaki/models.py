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


class Editor(models.Model):
    title = models.CharField(max_length=33)

    def __str__(self):
        return self.title


class Studio(models.Model):
    title = models.CharField(max_length=35)

    def __str__(self):
        return self.title


class Anime(Work):
    director = models.ForeignKey('Artist', related_name='directed', default=1)
    composer = models.ForeignKey('Artist', related_name='composed', default=1)
    studio = models.ForeignKey('Studio', default=1)
    author = models.ForeignKey('Artist', related_name='authored', default=1)
    editor = models.ForeignKey('Editor', default=1)
    anime_type = models.TextField(max_length=42, default='')
    genre = models.ManyToManyField('Genre')
    nb_episodes = models.TextField(default='Inconnu', max_length=16)
    origin = models.CharField(max_length=10, choices=ORIGIN_CHOICES, default='')

    def __str__(self):
        return self.title


class Manga(Work):
    vo_title = models.CharField(max_length=128)
    mangaka = models.ForeignKey('Artist', related_name='drew')
    writer = models.ForeignKey('Artist', related_name='wrote')
    editor = models.CharField(max_length=32)
    origin = models.CharField(max_length=10, choices=ORIGIN_CHOICES)
    genre = models.ManyToManyField('Genre')
    manga_type = models.TextField(max_length=16, choices=TYPE_CHOICES, blank=True)


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
    choice = models.CharField(max_length=8, choices=(
        ('favorite', 'Mon favori !'),
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
    nsfw_ok = models.BooleanField(default=False)
    avatar_url = models.CharField(max_length=128, default='', blank=True, null=True)
    mal_username = models.CharField(max_length=64, default='', blank=True, null=True)

    def get_anime_count(self):
        return Rating.objects.filter(user=self.user, choice__in=['like', 'neutral', 'dislike']).count()

    def get_avatar_url(self):
        if not self.avatar_url:
            avatar_url = get_discourse_data(self.user.email)['avatar'].format(size=150)
            self.avatar_url = avatar_url
            self.save()
        return self.avatar_url


class Suggestion(models.Model):
    user = models.ForeignKey(User)
    work = models.ForeignKey(Work)
    date = models.DateTimeField(auto_now=True)
    problem = models.CharField(verbose_name='Partie concernée', max_length=8, choices=(
        ('title', 'Le titre n\'est pas le bon'),
        ('poster', 'Le poster ne convient pas'),
        ('synopsis', 'Le synopsis comporte des erreurs'),
        ('author','L\'auteur n\'est pas le bon'),
        ('composer','Le compositeur n\'est pas le bon'),
        ('double','Ceci est un doublon'),
        ('nsfw','L\'oeuvre est NSFW'),
        ('n_nsfw','L\'oeuvre n\'est pas NSFW')
    ))
    message = models.TextField(verbose_name='Proposition', blank=True)
    is_checked = models.BooleanField(default=False)


class Neighborship(models.Model):
    user = models.ForeignKey(User)
    neighbor = models.ForeignKey(User, related_name='neighbor')
    score = models.DecimalField(decimal_places=3, max_digits=8)


class SearchIssue(models.Model):
    date = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User)
    title = models.CharField(max_length=128)
    poster = models.CharField(max_length=128, blank=True, null=True)
    mal_id = models.IntegerField(blank=True, null=True)
    score = models.IntegerField(blank=True, null=True)


class Announcement(models.Model):
    title = models.CharField(max_length=128)
    text = models.CharField(max_length=512)
    
    def __str__(self):
        return self.title

class Recommandation(models.Model):
    user = models.ForeignKey(User)
    target_user = models.ForeignKey(User, related_name='target_user')
    work = models.ForeignKey(Work)

    def __str__(self):
        return '%s recommends %s to %s' % (self.user, self.work, self.target_user)
