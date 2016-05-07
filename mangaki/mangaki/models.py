# coding=utf8
from django.db import models
from django.contrib.auth.models import User
from django.db.models import F, Q, Func, Value, Lookup, CharField
from django.db.models.functions import Coalesce
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

from mangaki.discourse import get_discourse_data
from mangaki.choices import ORIGIN_CHOICES, TYPE_CHOICES, TOP_CATEGORY_CHOICES
from mangaki.fields import CategoryField
from mangaki.utils.ranking import TOP_MIN_RATINGS, RANDOM_MIN_RATINGS, RANDOM_MAX_DISLIKES, RANDOM_RATIO

@CharField.register_lookup
class SearchLookup(Lookup):
    """Helper class for searching text in a query. This shadows the builtin
    __search django lookup, but we don't care because it doesn't work for
    PostgreSQL anyways."""

    lookup_name = 'search'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params + lhs_params + rhs_params
        return "(UPPER(F_UNACCENT(%s)) LIKE '%%%%' || UPPER(F_UNACCENT(%s)) || '%%%%' OR UPPER(F_UNACCENT(%s)) %%%% UPPER(F_UNACCENT(%s)))" % (lhs, rhs, lhs, rhs), params

class SearchSimilarity(Func):
    """Helper class for computing the search similarity ignoring case and
    accents"""

    function = 'SIMILARITY'

    def __init__(self, lhs, rhs):
        super().__init__(Func(Func(lhs, function='F_UNACCENT'), function='UPPER'), Func(Func(rhs, function='F_UNACCENT'), function='UPPER'))

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
        # We want to search when the title contains the query or when the
        # similarity between the title and the query is low; we also want to
        # show the relevant results first.
        return self.filter(title__search=search_text).\
            order_by(SearchSimilarity(F('title'), Value(search_text)).desc())


    def random(self):
        return self.filter(
            nb_ratings__gte=RANDOM_MIN_RATINGS,
            nb_dislikes__lte=RANDOM_MAX_DISLIKES,
            nb_likes__gte=F('nb_dislikes') * RANDOM_RATIO)

class Work(models.Model):
    title = models.CharField(max_length=128)
    source = models.CharField(max_length=1044, blank=True) # Rationale: JJ a trouvé que lors de la migration SQLite → PostgreSQL, bah il a pas trop aimé. (max_length empirique)
    poster = models.CharField(max_length=128)
    nsfw = models.BooleanField(default=False)
    date = models.DateField(blank=True, null=True)
    synopsis = models.TextField(blank=True, default='')
    category = CategoryField(blank=False, null=False)
    artists = models.ManyToManyField('Artist', through='Staff', blank=True)

    # Some of these fields do not make sense for some categories of works.
    genre = models.ManyToManyField('Genre')
    origin = models.CharField(max_length=10, choices=ORIGIN_CHOICES, default='', blank=True)
    nb_episodes = models.TextField(default='Inconnu', max_length=16, blank=True)
    anime_type = models.TextField(max_length=42, blank=True)
    vo_title = models.CharField(max_length=128, blank=True)
    manga_type = models.TextField(max_length=16, choices=TYPE_CHOICES, blank=True)
    catalog_number = models.CharField(max_length=20, blank=True)
    anidb_aid = models.IntegerField(default=0, blank=True)
    vgmdb_aid = models.IntegerField(blank=True, null=True)
    editor = models.ForeignKey('Editor', default=1)
    studio = models.ForeignKey('Studio', default=1)

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

    def get_absolute_url(self):
        return reverse('{}-detail'.format(self.category.slug), args=[str(self.id)])

    def safe_poster(self, user):
        if not self.nsfw or (user.is_authenticated() and user.profile.nsfw_ok):
            return self.poster
        return '/static/img/nsfw.jpg'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.pk and not hasattr(self, 'category'):
            if isinstance(self, Anime):
                self.category = 'anime'
            elif isinstance(self, Manga):
                self.category = 'manga'
            elif isinstance(self, Album):
                self.category = 'album'
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
    title = models.CharField(max_length=33, db_index=True)

    def __str__(self):
        return self.title


class Studio(models.Model):
    title = models.CharField(max_length=35)

    def __str__(self):
        return self.title


class Anime(Work):
    # Deprecated fields
    deprecated_director = models.ForeignKey('Artist', related_name='directed', default=1)
    deprecated_author = models.ForeignKey('Artist', related_name='authored', default=1)
    deprecated_composer = models.ForeignKey('Artist', related_name='composed', default=1)
    deprecated_genre = models.ManyToManyField('Genre')
    deprecated_origin = models.CharField(max_length=10, choices=ORIGIN_CHOICES, default='')
    deprecated_nb_episodes = models.TextField(default='Inconnu', max_length=16)
    deprecated_anime_type = models.TextField(max_length=42, default='')
    deprecated_anidb_aid = models.IntegerField(default=0)
    deprecated_editor = models.ForeignKey('Editor', default=1)
    deprecated_studio = models.ForeignKey('Studio', default=1)

    def __str__(self):
        return '[%d] %s' % (self.id, self.title)


class Manga(Work):
    # Deprecated fields
    deprecated_mangaka = models.ForeignKey('Artist', related_name='drew')
    deprecated_writer = models.ForeignKey('Artist', related_name='wrote')
    deprecated_genre = models.ManyToManyField('Genre')
    deprecated_origin = models.CharField(max_length=10, choices=ORIGIN_CHOICES)
    deprecated_vo_title = models.CharField(max_length=128)
    deprecated_manga_type = models.TextField(max_length=16, choices=TYPE_CHOICES, blank=True)
    deprecated_editor = models.CharField(max_length=32)


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
    # Deprecated fields
    deprecated_composer = models.ForeignKey('Artist', related_name='composer', default=1)
    deprecated_catalog_number = models.CharField(max_length=20)
    deprecated_vgmdb_aid = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return '[{id}] {title}'.format(id=self.id, title=self.title)

class Artist(models.Model):
    first_name = models.CharField(max_length=32, blank=True, null=True)  # No longer used
    last_name = models.CharField(max_length=32)  # No longer used
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class ArtistSpelling(models.Model):
    was = models.CharField(max_length=255, db_index=True)
    artist = models.ForeignKey('Artist')


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

    class Meta:
        unique_together = ('user', 'work')

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
