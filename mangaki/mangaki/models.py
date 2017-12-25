# coding=utf-8
import os.path
import tempfile
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.search import SearchVectorField
from django.core.files import File
from django.core.urlresolvers import reverse
from django.db import models, transaction
from django.db.models import CharField, F, Func, Lookup, Value, Q, FloatField, ExpressionWrapper
from django.db.models.functions import Cast
from django.utils.functional import cached_property

from mangaki.choices import (ORIGIN_CHOICES, TOP_CATEGORY_CHOICES, TYPE_CHOICES,
                             CLUSTER_CHOICES, RELATION_TYPE_CHOICES, SUGGESTION_PROBLEM_CHOICES)
from mangaki.utils.ranking import (TOP_MIN_RATINGS, RANDOM_MIN_RATINGS, RANDOM_MAX_DISLIKES, RANDOM_RATIO,
                                   PEARLS_MIN_RATINGS, PEARLS_MAX_RATINGS, PEARLS_MAX_DISLIKE_RATE)
from mangaki.utils.dpp import MangakiDPP


TOP_POPULAR_WORKS_FOR_SAMPLING = 200


@CharField.register_lookup
class SearchLookup(Lookup):
    """Helper class for searching text in a query. This shadows the builtin
    __search django lookup, but we don't care because it doesn't work for
    PostgreSQL anyways."""

    lookup_name = 'mangaki_search'

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


class FilteredWorkManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(redirect__isnull=True)


class WorkQuerySet(models.QuerySet):
    # There are indexes in the database related to theses queries. Please don't
    # change the formulaes without issuing the appropriate migrations.
    def top(self):
        return self.filter(
            nb_ratings__gte=TOP_MIN_RATINGS).order_by(
                (F('sum_ratings') / F('nb_ratings')).desc())

    def pearls(self):
        return (self.exclude(nb_likes=0)
                    .annotate(
                        dislike_rate=ExpressionWrapper(
                            Cast(F('nb_dislikes'), FloatField()) / F('nb_likes'), output_field=FloatField())
                    )
                    .filter(nb_ratings__gte=PEARLS_MIN_RATINGS, nb_ratings__lte=PEARLS_MAX_RATINGS, dislike_rate__lte=PEARLS_MAX_DISLIKE_RATE)
                    .order_by('dislike_rate'))

    def popular(self):
        return self.order_by('-nb_ratings')

    def controversial(self):
        return self.order_by('-controversy')

    def search(self, search_text):
        # We want to search when the title contains the query or when the
        # similarity between the title and the query is low; we also want to
        # show the relevant results first.
        return self.filter(title__mangaki_search=search_text).\
            order_by(SearchSimilarity(F('title'), Value(search_text)).desc())

    def dpp(self, nb_works):
        """
        sample "nb_points" popular works which are far from each other (using DPP)
        """
        work_ids = self.popular()[:TOP_POPULAR_WORKS_FOR_SAMPLING].values_list('id', flat=True)
        dpp = MangakiDPP(work_ids)
        dpp.load_from_algo('svd')
        sampled_work_ids = dpp.sample_k(nb_works)
        return self.filter(id__in=sampled_work_ids)

    def random(self):
        return self.filter(
            nb_ratings__gte=RANDOM_MIN_RATINGS,
            nb_dislikes__lte=RANDOM_MAX_DISLIKES,
            nb_likes__gte=F('nb_dislikes') * RANDOM_RATIO)

    def group_by_category(self):
        """
        Groups this queryset by category. This returns a dictionnary mapping
        categories to the corresponding works in the queryset.

        Returns:
          by_category -- A mapping from category IDs to the list of works in
              this queryset in the corresponding category. Order inside a
              category is preserved.
        """
        by_category = {}
        for work in self:
            by_category.setdefault(work.category_id, []).append(work)

        return by_category

class Category(models.Model):
    slug = models.CharField(max_length=10, db_index=True)
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class Work(models.Model):
    redirect = models.ForeignKey('Work', blank=True, null=True)
    title = models.CharField(max_length=255)
    source = models.CharField(max_length=1044, blank=True) # Rationale: JJ a trouvé que lors de la migration SQLite → PostgreSQL, bah il a pas trop aimé. (max_length empirique)
    ext_poster = models.CharField(max_length=128, db_index=True)
    int_poster = models.FileField(upload_to='posters/', blank=True, null=True)
    nsfw = models.BooleanField(default=False)
    date = models.DateField(blank=True, null=True) # Should be renamed to start_date
    end_date = models.DateField(blank=True, null=True)
    synopsis = models.TextField(blank=True, default='')
    ext_synopsis = models.TextField(blank=True, default='')
    category = models.ForeignKey('Category', blank=False, null=False, on_delete=models.PROTECT)
    artists = models.ManyToManyField('Artist', through='Staff', blank=True)

    # Some of these fields do not make sense for some categories of works.
    genre = models.ManyToManyField('Genre')
    tags = models.ManyToManyField('Tag', through="TaggedWork")
    origin = models.CharField(max_length=10, choices=ORIGIN_CHOICES, default='', blank=True)
    nb_episodes = models.TextField(default='Inconnu', max_length=16, blank=True)
    anime_type = models.TextField(max_length=42, blank=True)
    vo_title = models.CharField(max_length=128, blank=True)
    manga_type = models.TextField(max_length=16, choices=TYPE_CHOICES, blank=True)
    catalog_number = models.CharField(max_length=20, blank=True)
    anidb_aid = models.IntegerField(default=0, blank=True)
    vgmdb_aid = models.IntegerField(blank=True, null=True)
    editor = models.ForeignKey('Editor', null=True, on_delete=models.PROTECT)
    studio = models.ForeignKey('Studio', null=True, on_delete=models.PROTECT)

    # Cache fields for the rankings
    sum_ratings = models.FloatField(blank=True, null=False, default=0)
    nb_ratings = models.IntegerField(blank=True, null=False, default=0)
    nb_likes = models.IntegerField(blank=True, null=False, default=0)
    nb_dislikes = models.IntegerField(blank=True, null=False, default=0)
    controversy = models.FloatField(blank=True, null=False, default=0)

    # Cache fields for the title deduplication
    title_search = SearchVectorField('title')

    class Meta:
        index_together = [
            ['category', 'controversy'],
            ['category', 'nb_ratings'],
        ]

    objects = FilteredWorkManager.from_queryset(WorkQuerySet)()
    all_objects = WorkQuerySet.as_manager()

    def get_absolute_url(self):
        return reverse('work-detail', args=[self.category.slug, str(self.id)])

    @property
    def poster_url(self):
        if self.int_poster:
            return self.int_poster.url
        return self.ext_poster

    def safe_poster(self, user):
        if self.id is None:
            return '{}{}'.format(settings.STATIC_URL, 'img/chiro.gif')
        if not self.nsfw or (user.is_authenticated and user.profile.nsfw_ok):
            return self.poster_url
        return '{}{}'.format(settings.STATIC_URL, 'img/nsfw.jpg')

    def retrieve_poster(self, url=None, session=None):
        if session is None:
            session = requests
        if url is None:
            url = self.ext_poster
        if not url:
            return False

        poster_filename = "{:d}-{:s}".format(self.id, os.path.basename(urlparse(url).path))
        # FIXME: Add a get_poster_filename with hash, and use it everywhere

        try:
            r = session.get(url, timeout=5, stream=True)
        except requests.RequestException as e:
            return False

        try:
            with tempfile.TemporaryFile() as f:
                for chunk in r.iter_content(chunk_size=1024):
                    f.write(chunk)
                self.ext_poster = url
                self.int_poster.save(poster_filename, File(f))
        finally:
            r.close()
        return True

    def __str__(self):
        return self.title


class WorkTitle(models.Model):
    work = models.ForeignKey('Work')
    # 255 should be safe, we have seen titles of 187 characters in Japanese.
    # So we could expect longer titles in English.
    title = models.CharField(max_length=255, blank=True, db_index=True)
    title_search = SearchVectorField('title')
    language = models.ForeignKey('Language',
                                 null=True)
    ext_language = models.ForeignKey('ExtLanguage',
                                     null=True)
    type = models.CharField(max_length=9, choices=(
                            ('main', 'principal'),
                            ('official', 'officiel'),
                            ('synonym', 'synonyme'),
                            ('short', 'court')),
                            blank=True,
                            db_index=True)

    @cached_property
    def code(self):
        return self.language.code if self.language else None

    @cached_property
    def source(self):
        return self.ext_language.source if self.ext_language else None

    def __str__(self):
        if self.code and self.source:
            return ("{} - {} (source: {}, type: {}) attached to {}"
                    .format(self.title, self.code, self.source, self.type, self.work))
        elif self.source:
            return ("{} (source: {}, type: {}) attached to {}"
                    .format(self.title, self.source, self.type, self.work))
        elif self.code:
            return ("{} - {} (type: {}) attached to {}"
                    .format(self.title, self.code, self.type, self.work))
        else:
            return ("{} (type: {}) attached to {}"
                    .format(self.title, self.type, self.work))


class ExtLanguage(models.Model):
    source = models.CharField(max_length=30)
    ext_lang = models.CharField(
        null=True,
        max_length=8,
        db_index=True
    )
    lang = models.ForeignKey('Language')

    class Meta:
        unique_together = ('ext_lang', 'source')

    def __str__(self):
        return ('<ExtLanguage: source {}, ext_lang: {}, lang: {}>'
                .format(self.source,
                        self.ext_lang,
                        self.lang.code))


class Language(models.Model):
    code = models.CharField(
        default=None,
        null=True,
        unique=True,
        max_length=10,
        db_index=True,
        help_text="ISO639-1 code or custom (e.g. x-jat, x-kot, x-ins)")

    def __str__(self):
        return self.code if self.code else 'inconnu'


class Role(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return '{} /{}/'.format(self.name, self.slug)


class Staff(models.Model):
    work = models.ForeignKey('Work', on_delete=models.CASCADE)
    artist = models.ForeignKey('Artist', on_delete=models.CASCADE)
    role = models.ForeignKey('Role', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('work', 'artist', 'role')

    def __str__(self):
        return "{}, {} de {}" .format(
            self.artist.name,
            self.role.name.lower(),
            self.work.title)


class Editor(models.Model):
    title = models.CharField(max_length=33, db_index=True)

    def __str__(self):
        return self.title


class Studio(models.Model):
    title = models.CharField(max_length=35)

    def __str__(self):
        return self.title


class Genre(models.Model):
    title = models.CharField(max_length=17)

    def __str__(self):
        return self.title


class Tag(models.Model):
    title = models.CharField(max_length=255)
    anidb_tag_id = models.IntegerField(unique=True)

    def __str__(self):
        return self.title


class TaggedWork(models.Model):
    work = models.ForeignKey('Work')
    tag = models.ForeignKey('Tag')
    weight = models.IntegerField(default=0)

    class Meta:
        unique_together = ('work', 'tag')

    def __str__(self):
        return "%s %s %s" % (self.work, self.tag, self.weight)


class RelatedWork(models.Model):
    parent_work = models.ForeignKey('Work', on_delete=models.CASCADE, related_name='parent_work')
    child_work = models.ForeignKey('Work', on_delete=models.CASCADE, related_name='child_work')
    type = models.CharField(
        verbose_name='Type de relation',
        max_length=20,
        choices=RELATION_TYPE_CHOICES,
        default=''
    )

    class Meta:
        unique_together = ('parent_work', 'child_work', 'type')

    def __str__(self):
        return "%s : %s de %s" % (self.child_work, self.type, self.parent_work)


class Track(models.Model):
    title = models.CharField(max_length=32)
    album = models.ManyToManyField('Work')

    def __str__(self):
        return self.title


class Artist(models.Model):
    name = models.CharField(max_length=255)
    anidb_creator_id = models.IntegerField(null=True, unique=True)
    anilist_creator_id = models.IntegerField(null=True, unique=True)

    def __str__(self):
        return self.name


class ArtistSpelling(models.Model):
    was = models.CharField(max_length=255, db_index=True)
    artist = models.ForeignKey('Artist', on_delete=models.CASCADE)


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    choice = models.CharField(max_length=8, choices=(
        ('favorite', 'Mon favori !'),
        ('like', "J'aime"),
        ('dislike', "Je n'aime pas"),
        ('neutral', 'Neutre'),
        ('willsee', 'Je veux voir'),
        ('wontsee', 'Je ne veux pas voir')
    ))
    date = models.DateTimeField(auto_now=True)

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
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_shared = models.BooleanField(default=True)
    nsfw_ok = models.BooleanField(default=False)
    newsletter_ok = models.BooleanField(default=True)
    reco_willsee_ok = models.BooleanField(default=False)
    research_ok = models.BooleanField(default=True)
    keyboard_shortcuts_enabled = models.BooleanField(default=False)
    avatar_url = models.CharField(max_length=128, default='', blank=True, null=True)
    mal_username = models.CharField(max_length=64, default='', blank=True, null=True)

    def get_anime_count(self):
        return Rating.objects.filter(user=self.user, choice__in=['like', 'neutral', 'dislike', 'favorite']).count()


class Suggestion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now=True)
    problem = models.CharField(verbose_name='Partie concernée', max_length=8, choices=SUGGESTION_PROBLEM_CHOICES, default='ref')
    message = models.TextField(verbose_name='Proposition', blank=True)
    is_checked = models.BooleanField(default=False)

    def __str__(self):
        return 'Suggestion#{} de {} : {} - {}'.format(
            self.pk, self.user, self.work.title, self.get_problem_display()
        )

    @property
    def can_auto_fix(self):
        # FIXME: use Enum + dynamic based on evidences / message (links).
        return self.problem in ('nsfw', 'n_nsfw')

    @transaction.atomic
    def auto_fix(self):
        """
        Apply automatically a fix on the issue.
        e.g. for a NSFW (resp. non-NSFW) problem, it'll set the work as NSFW (resp. non-NSFW).

        It'll raise ValueError when it is impossible to automatically fix the issue.
        """
        if self.problem in ('nsfw', 'n_nsfw'):
            self.work.nsfw = True if self.problem == 'nsfw' else False
            self.work.save()
        else:
            raise ValueError('Unable to auto-fix `{}`-type suggestions.'.format(self.problem))

        self.is_checked = True
        self.save()


class Evidence(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    suggestion = models.ForeignKey(Suggestion, on_delete=models.CASCADE)
    agrees = models.BooleanField(default=False)
    needs_help = models.BooleanField(default=False)

    def __str__(self):
        return 'Evidence#{} : {} {} la Suggestion#{}'.format(
            self.pk,
            self.user,
            "approuve" if self.agrees else "rejette",
            self.suggestion.pk
        )


class WorkCluster(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    works = models.ManyToManyField(Work)
    reported_on = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=11, choices=CLUSTER_CHOICES, default='unprocessed')
    checker = models.ForeignKey(User, related_name='reported_clusters', on_delete=models.CASCADE, blank=True, null=True)
    resulting_work = models.ForeignKey(Work, related_name='clusters', blank=True, null=True)
    merged_on = models.DateTimeField(blank=True, null=True)
    origin = models.ForeignKey(Suggestion, related_name='origin_suggestion', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return 'WorkCluster ({})'.format(', '.join(self.works))


class Announcement(models.Model):
    title = models.CharField(max_length=128)
    text = models.CharField(max_length=512)

    def __str__(self):
        return self.title


class Recommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    target_user = models.ForeignKey(User, related_name='target_user', on_delete=models.CASCADE)
    work = models.ForeignKey(Work, on_delete=models.CASCADE)

    def __str__(self):
        return '%s recommends %s to %s' % (self.user, self.work, self.target_user)


class Pairing(models.Model):
    date = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    work = models.ForeignKey(Work, on_delete=models.CASCADE)
    is_checked = models.BooleanField(default=False)


class Reference(models.Model):
    work = models.ForeignKey('Work', on_delete=models.CASCADE)
    source = models.CharField(max_length=100)
    identifier = models.CharField(max_length=512)
    url = models.CharField(max_length=512)
    suggestions = models.ManyToManyField('Suggestion', blank=True)

    class Meta:
        unique_together = (
            ('work', 'source', 'identifier'),
        )


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


class ColdStartRating(models.Model):
    user = models.ForeignKey(User, related_name='cold_start_rating')
    work = models.ForeignKey(Work)
    choice = models.CharField(max_length=8, choices=(
        ('like', 'J\'aime'),
        ('dislike', 'Je n\'aime pas'),
        ('dontknow', 'Je ne connais pas')
    ))
    date = models.DateField(auto_now=True)

    class Meta:
        unique_together = ('user', 'work')

    def __str__(self):
        return '%s %s %s' % (self.user, self.choice, self.work)


class FAQTheme(models.Model):
    order = models.IntegerField(unique=True)
    theme = models.CharField(max_length=200)

    def __str__(self):
        return self.theme

    class Meta:
        verbose_name_plural = "FAQ themes"


class FAQEntry(models.Model):
    theme = models.ForeignKey(FAQTheme, on_delete=models.CASCADE, related_name="entries")
    question = models.CharField(max_length=200)
    answer = models.TextField()
    pub_date = models.DateTimeField('Date de publication', auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.question

    class Meta:
        verbose_name_plural = "FAQ entries"

class Trope(models.Model):
    trope = models.CharField(max_length=320)
    author = models.CharField(max_length=80)
    origin = models.ForeignKey(Work, on_delete=models.CASCADE)

    def __str__(self):
        return self.trope


class UserBackgroundTask(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='background_tasks')
    task_id = models.CharField(max_length=80)
    tag = models.CharField(max_length=80)  # For custom usage of tasks.

    def __str__(self):
        return '<{} owned by {}>'.format(self.tag, self.owner)


class UserArchive(models.Model):
    updated_on = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    local_archive = models.FileField(upload_to='user_archives/')

    def __str__(self):
        try:
            return '<UserArchive owned by {} at {}>'.format(self.owner, self.local_archive.path)
        except ValueError:
            return '<Empty UserArchive owned by {}>'.format(self.owner)
