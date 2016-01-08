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
    anidb_aid = models.IntegerField(default=0)

    def __str__(self):
        return '[%d] %s' % (self.id, self.title)


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
    newsletter_ok = models.BooleanField(default=True)
    reco_willsee_ok = models.BooleanField(default=False)
    avatar_url = models.CharField(max_length=128, default='', blank=True, null=True)
    mal_username = models.CharField(max_length=64, default='', blank=True, null=True)
    score = models.IntegerField(default=0)

    def get_anime_count(self):
        return Rating.objects.filter(user=self.user, choice__in=['like', 'neutral', 'dislike', 'favorite']).count()

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
        ('author', 'L\'auteur n\'est pas le bon'),
        ('composer', 'Le compositeur n\'est pas le bon'),
        ('double', 'Ceci est un doublon'),
        ('nsfw', 'L\'oeuvre est NSFW'),
        ('n_nsfw', 'L\'oeuvre n\'est pas NSFW'),
        ('ref', 'Proposer une URL (myAnimeList, AniDB, Icotaku, VGMdb, etc.)')
    ), default='ref')
    message = models.TextField(verbose_name='Proposition', blank=True)
    is_checked = models.BooleanField(default=False)

    def current_work_data(self):
        include_bootstrap = '    <link rel="stylesheet" href="/static/css/bootstrap.min.css" /><link rel="stylesheet" href="/static/css/bootstrap-switch.min.css" /><link rel="stylesheet" href="/static/css/typeahead.css" /><link rel="stylesheet" href="/static/css/skin.css" /><link rel="stylesheet" href="/static/css/test.css" />'
        title = '<h1>' + self.work.title + '</h1>'
        poster = '<div style="background-image: url(\'' + self.work.poster + '\'); background-repeat: no-repeat; position: center; background-size: 100%; background-position: center; height: 350px; max-width: 225px; margin-left: auto; margin-right: auto"></div>'
        synopsis = '<div class="well">' + self.work.synopsis + '</div>'
        try:
            self.work.manga
        except AttributeError:
            editor = '<div>Éditeur : ' + str(self.work.anime.editor) + '</div>'
            origin = '<div>Origine : ' + self.work.anime.origin + '</div>'
            genres_list = []
            for genre in self.work.anime.genre.all():
                genres_list.append(genre.title)
            genres = '<div>Genres : ' + ', '.join(genres_list) + '</div>'
            work_type = '<div>Type : ' + self.work.anime.anime_type + '</div>'
            author = '<div>Auteur : ' + str(self.work.anime.author) + '</div>'
            nb_episodes = '<div>Nombre d\'épisodes : ' + self.work.anime.nb_episodes + '</div>'
            data = nb_episodes + author + editor + origin + genres + work_type
            link = '<div><a href="/admin/mangaki/anime/' + str(self.work.id) + '/"><b>Éditer les informations</b></a></div>'
        else:
            editor = '<div>Éditeur : ' + str(self.work.manga.editor.title) + '</div>'
            origin = '<div>Origine : ' + self.work.manga.origin + '</div>'
            genres_list = []
            for genre in self.work.manga.genre.all():
                genres_list.append(genre.title)
            genres = '<div>Genres : ' + ', '.join(genres_list) + '</div>'
            work_type = '<div>Type : ' + self.work.manga.manga_type + '</div>'
            mangaka = '<div>Dessin : ' + str(self.work.manga.mangaka) + '</div>'
            writer = '<div>Scénario : ' + str(self.work.manga.writer) + '</div>'
            vo_title = '<div>Titre original : ' + self.work.manga.vo_title + '</div>'
            data = vo_title + mangaka + writer + editor + origin + genres + work_type
            link = '<div><a href="/admin/mangaki/manga/' + str(self.work.id) + '/"><b>Éditer les informations</b></a></div>'
        return include_bootstrap + '<div class="row"><div class="col-xs-2">' + poster + '</div><div class="col-xs-7">' + title + '<br/>' + data + '<br/>' + synopsis + link + '</div></div>'
    current_work_data.allow_tags = True

    def update_scores(self):
        suggestions_score = 5 * Suggestion.objects.filter(user=self.user, is_checked=True).count()
        recommendations_score = 0
        reco_list = Recommendation.objects.filter(user=self.user)
        for reco in reco_list:
            if Rating.objects.filter(user=reco.target_user, work=reco.work, choice='like').count() > 0:
                recommendations_score += 1
            if Rating.objects.filter(user=reco.target_user, work=reco.work, choice='favorite').count() > 0:
                recommendations_score += 5
        score = suggestions_score + recommendations_score
        Profile.objects.filter(user=self.user).update(score=score)


def suggestion_saved(sender, instance, *args, **kwargs):
    instance.update_scores()
models.signals.post_save.connect(suggestion_saved, sender=Suggestion)


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


class Recommendation(models.Model):
    user = models.ForeignKey(User)
    target_user = models.ForeignKey(User, related_name='target_user')
    work = models.ForeignKey(Work)

    def __str__(self):
        return '%s recommends %s to %s' % (self.user, self.work, self.target_user)


class Pairing(models.Model):
    date = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User)
    artist = models.ForeignKey(Artist)
    work = models.ForeignKey(Work)
    is_checked = models.BooleanField(default=False)


class Deck(models.Model):
    category = models.CharField(max_length=32)
    sort_mode = models.CharField(max_length=32)
    content = models.CommaSeparatedIntegerField(max_length=42000)


class Reference(models.Model):
    work = models.ForeignKey('Work')
    url = models.CharField(max_length=512)
    suggestions = models.ManyToManyField('Suggestion', blank=True)
