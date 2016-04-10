# coding=utf8
from django.db import models
from django.contrib.auth.models import User
from django.db.models import F, Q, Func, Value
from django.db.models.functions import Coalesce
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from mangaki.discourse import get_discourse_data
from mangaki.choices import ORIGIN_CHOICES, TYPE_CHOICES, TOP_CATEGORY_CHOICES
from mangaki.utils.ranking import TOP_MIN_RATINGS, RANDOM_MIN_RATINGS, RANDOM_MAX_DISLIKES, RANDOM_RATIO

from unidecode import unidecode

class WorkQuerySet(models.QuerySet):
    # There are indexes in the database related to theses queries. Please don't
    # change the formulaes without issuing the appropriate migrations.
    def top(self):
        return self.filter(
            nb_ratings__gte=TOP_MIN_RATINGS).order_by(
                (F('sum_ratings') / F('nb_ratings')).desc())

    def popular(self):
        return self.order_by('-nb_ratings')

    def controversial(self):
        return self.order_by('-controversy')

    def search(self, search_text):
        return self.annotate(sim_score=Func(Func(F('title'), function='UNACCENT'), Value(unidecode(search_text)), function='SIMILARITY'))\
                .annotate(unaccent_title=Func(F('title'), function='UNACCENT'))\
                .filter(Q(unaccent_title__icontains=unidecode(search_text)) | Q(sim_score__gte=Func(function='SHOW_LIMIT'))).\
                order_by('-sim_score')


    def random(self):
        return self.filter(
            nb_ratings__gte=RANDOM_MIN_RATINGS,
            nb_dislikes__lte=RANDOM_MAX_DISLIKES,
            nb_likes__gte=F('nb_dislikes') * RANDOM_RATIO)

class Category(models.Model):
    slug = models.CharField(max_length=10, db_index=True)
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name

class Work(models.Model):
    title = models.CharField(max_length=128)
    source = models.CharField(max_length=1044, blank=True) # Rationale: JJ a trouvé que lors de la migration SQLite → PostgreSQL, bah il a pas trop aimé. (max_length empirique)
    poster = models.CharField(max_length=128)
    nsfw = models.BooleanField(default=False)
    date = models.DateField(blank=True, null=True)
    synopsis = models.TextField(blank=True, default='')
    category = models.ForeignKey('Category', blank=True, null=False)
    artists = models.ManyToManyField('Artist', through='Staff', blank=True)

    # Cache fields for the rankings
    sum_ratings = models.FloatField(blank=True, null=False, default=0)
    nb_ratings = models.IntegerField(blank=True, null=False, default=0)
    nb_likes = models.IntegerField(blank=True, null=False, default=0)
    nb_dislikes = models.IntegerField(blank=True, null=False, default=0)
    controversy = models.FloatField(blank=True, null=False, default=0)

    class Meta:
        index_together = [
            ['category', 'controversy'],
            ['category', 'nb_ratings'],
        ]

    objects = WorkQuerySet.as_manager()

    def safe_poster(self, user):
        if not self.nsfw or (user.is_authenticated() and user.profile.nsfw_ok):
            return self.poster
        return '/static/img/nsfw.jpg'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.pk:
            if isinstance(self, Anime):
                self.category = Category.objects.get(slug='anime')
            elif isinstance(self, Manga):
                self.category = Category.objects.get(slug='manga')
            elif isinstance(self, Album):
                self.category = Category.objects.get(slug='album')
            else:
                raise TypeError('Unexpected subclass of work: {}'.format(type(self)))
        super().save(*args, **kwargs)

class Role(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return '{} /{}/'.format(self.name, self.slug)

class Staff(models.Model):
    work = models.ForeignKey('Work')
    artist = models.ForeignKey('Artist')
    role = models.ForeignKey('Role')

    class Meta:
        unique_together = ('work', 'artist', 'role')

class Editor(models.Model):
    title = models.CharField(max_length=33)

    def __str__(self):
        return self.title


class Studio(models.Model):
    title = models.CharField(max_length=35)

    def __str__(self):
        return self.title


class Anime(Work):
    studio = models.ForeignKey('Studio', default=1)
    editor = models.ForeignKey('Editor', default=1)
    anime_type = models.TextField(max_length=42, default='')
    genre = models.ManyToManyField('Genre')
    nb_episodes = models.TextField(default='Inconnu', max_length=16)
    origin = models.CharField(max_length=10, choices=ORIGIN_CHOICES, default='')
    anidb_aid = models.IntegerField(default=0)

    # Deprecated fields
    deprecated_director = models.ForeignKey('Artist', related_name='directed', default=1)
    deprecated_author = models.ForeignKey('Artist', related_name='authored', default=1)
    deprecated_composer = models.ForeignKey('Artist', related_name='composed', default=1)

    def __str__(self):
        return '[%d] %s' % (self.id, self.title)


class Manga(Work):
    vo_title = models.CharField(max_length=128)
    editor = models.CharField(max_length=32)
    origin = models.CharField(max_length=10, choices=ORIGIN_CHOICES)
    genre = models.ManyToManyField('Genre')
    manga_type = models.TextField(max_length=16, choices=TYPE_CHOICES, blank=True)

    # Deprecated fields
    deprecated_mangaka = models.ForeignKey('Artist', related_name='drew')
    deprecated_writer = models.ForeignKey('Artist', related_name='wrote')


class Genre(models.Model):
    title = models.CharField(max_length=17)

    def __str__(self):
        return self.title


class Track(models.Model):
    title = models.CharField(max_length=32)
    album = models.ManyToManyField('Album')

    def __str__(self):
        return self.title


class Album(Work):
    composer = models.ForeignKey('Artist', related_name='composer', default=1)
    catalog_number = models.CharField(max_length=20)
    vgmdb_aid = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return '[{id}] {title}'.format(id=self.id, title=self.title)

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
    date = models.DateField(auto_now=True)

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


class Reference(models.Model):
    work = models.ForeignKey('Work')
    url = models.CharField(max_length=512)
    suggestions = models.ManyToManyField('Suggestion', blank=True)

class Top(models.Model):
    date = models.DateField(auto_now_add=True)
    category = models.CharField(max_length=10, choices=TOP_CATEGORY_CHOICES, unique_for_date='date')

    contents = models.ManyToManyField(ContentType, through='Ranking')

    def __str__(self):
        return 'Top {category} on {date} (id={id})'.format(
            category=self.category,
            date=self.date,
            id=self.id)

class Ranking(models.Model):
    top = models.ForeignKey('Top', on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    score = models.FloatField()
    nb_ratings = models.PositiveIntegerField()
    nb_stars = models.PositiveIntegerField()
