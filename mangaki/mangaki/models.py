# coding=utf8
import os.path
import tempfile
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import CharField, F, Func, Lookup, Value

from mangaki.choices import ORIGIN_CHOICES, TOP_CATEGORY_CHOICES, TYPE_CHOICES
from mangaki.utils.ranking import TOP_MIN_RATINGS, RANDOM_MIN_RATINGS, RANDOM_MAX_DISLIKES, RANDOM_RATIO
from mangaki.utils.dpp import MangakiDPP
from mangaki.utils.ratingsmatrix import RatingsMatrix

TOP_POPULAR_WORKS_FOR_SAMPLING = 200


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
    title = models.CharField(max_length=128)
    source = models.CharField(max_length=1044, blank=True) # Rationale: JJ a trouvé que lors de la migration SQLite → PostgreSQL, bah il a pas trop aimé. (max_length empirique)
    ext_poster = models.CharField(max_length=128)
    int_poster = models.FileField(upload_to='posters/', blank=True, null=True)
    nsfw = models.BooleanField(default=False)
    date = models.DateField(blank=True, null=True)
    synopsis = models.TextField(blank=True, default='')
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
    editor = models.ForeignKey('Editor', default=1, on_delete=models.PROTECT)
    studio = models.ForeignKey('Studio', default=1, on_delete=models.PROTECT)

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
        return reverse('work-detail', args=[self.category.slug, str(self.id)])

    def retrieve_tags(self, anidb):
        anidb_tags_list = anidb.get(self.anidb_aid).tags
        anidb_tags = {title: int(weight) for title, weight in anidb_tags_list}

        tag_work = TaggedWork.objects.filter(work=self)
        current_tags = {tagwork.tag.title: tagwork.weight for tagwork in tag_work}

        deleted_tags_keys = current_tags.keys() - anidb_tags.keys()
        deleted_tags = {key: current_tags[key] for key in deleted_tags_keys}

        added_tags_keys = anidb_tags.keys() - current_tags.keys()
        added_tags = {key: anidb_tags[key] for key in added_tags_keys}

        remaining_tags_keys = anidb_tags.keys() & current_tags.keys()
        remaining_tags = {key: current_tags[key] for key in remaining_tags_keys}

        updated_tags = {title: (current_tags[title], anidb_tags[title]) for title in remaining_tags if current_tags[title] != anidb_tags[title]}
        kept_tags = {title: current_tags[title] for title in remaining_tags if current_tags[title] == anidb_tags[title]}

        return {"deleted_tags": deleted_tags, "added_tags": added_tags, "updated_tags": updated_tags, "kept_tags": kept_tags}

    def update_tags(self, deleted_tags, added_tags, updated_tags):
        for title, weight in added_tags.items():
            current_tag = Tag.objects.get_or_create(title=title)[0]
            TaggedWork(tag=current_tag, work=self, weight=weight).save()

        tags = Tag.objects.filter(title__in=updated_tags.keys())
        for tag in tags:
            tagged_work = self.taggedwork_set.get(tag=tag)
            tagged_work.weight = updated_tags[tag.title][1]
            tagged_work.save()

        TaggedWork.objects.filter(work=self, tag__title__in=deleted_tags.keys()).delete()

    def safe_poster(self, user):
        if self.id is None:
            return '{}{}'.format(settings.STATIC_URL, 'img/chiro.gif')
        if not self.nsfw or (user.is_authenticated and user.profile.nsfw_ok):
            if self.int_poster:
                return self.int_poster.url
            return self.ext_poster
        return '{}{}'.format(settings.STATIC_URL, 'img/nsfw.jpg')

    def retrieve_poster(self, url=None, session=None):
        if session is None:
            session = requests
        if url is None:
            url = self.ext_poster
        if not url:
            return False

        filename = os.path.basename(urlparse(url).path)
        # Hé mais ça va pas écraser des posters / créer des collisions, ça ?

        try:
            r = session.get(url, timeout=5, stream=True)
        except requests.RequestException as e:
            return False

        try:
            with tempfile.TemporaryFile() as f:
                for chunk in r.iter_content(chunk_size=1024):
                    f.write(chunk)
                self.ext_poster = url
                self.int_poster.save(filename, File(f))
        finally:
            r.close()
        return True

    def __str__(self):
        return self.title


class WorkTitle(models.Model):
    work = models.ForeignKey('Work')
    title = models.CharField(max_length=128, blank=True, db_index=True)
    language = models.ForeignKey('Language',
                                 null=True)
    type = models.CharField(max_length=9, choices=(
                            ('main', 'principal'),
                            ('official', 'officiel'),
                            ('synonym', 'synonyme')),
                            blank=True,
                            db_index=True)

    def __str__(self):
        return "%s" % self.title


class Language(models.Model):
    anidb_language = models.CharField(max_length=5,
                                      blank=True,
                                      db_index=True)
    iso639 = models.CharField(max_length=2,
                            unique=True,
                            db_index=True)

    def __str__(self):
        return "%s : %s" % (self.anidb_language, self.iso639)


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
    title = models.TextField(unique = True)

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


class Track(models.Model):
    title = models.CharField(max_length=32)
    album = models.ManyToManyField('Work')

    def __str__(self):
        return self.title


class Artist(models.Model):
    name = models.CharField(max_length=255)
    anidb_creator_id = models.IntegerField(null=True, unique=True)

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


class Suggestion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    work = models.ForeignKey(Work, on_delete=models.CASCADE)
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


class Neighborship(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    neighbor = models.ForeignKey(User, related_name='neighbor', on_delete=models.CASCADE)
    score = models.DecimalField(decimal_places=3, max_digits=8)


class SearchIssue(models.Model):
    date = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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


class FAQEntry(models.Model):
    theme = models.ForeignKey(FAQTheme, on_delete=models.CASCADE, related_name="entries")
    question = models.CharField(max_length=200)
    answer = models.TextField()
    pub_date = models.DateTimeField('Date de publication', auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.question

class Trope(models.Model): 
    trope = models.CharField(max_length=320)
    author = models.CharField(max_length=80)
    origin = models.ForeignKey(Work, on_delete=models.CASCADE)

    def __str__(self):
        return self.trope
