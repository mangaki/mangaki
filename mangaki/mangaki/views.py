from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import FormMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.timezone import utc

from django.dispatch import receiver
from django.db.models import Count
from django.db import connection
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added
from mangaki.models import Work, Anime, Manga, Album, Rating, Page, Profile, Artist, Suggestion, SearchIssue, Announcement, Recommendation, Pairing, Deck, Top, Ranking
from mangaki.mixins import AjaxableResponseMixin
from mangaki.forms import SuggestionForm
from mangaki.utils.mal import lookup_mal_api, import_mal, retrieve_anime
from mangaki.utils.recommendations import get_recommendations
from mangaki.utils.chrono import Chrono
from irl.models import Event, Partner, Attendee

from collections import Counter
from markdown import markdown
from urllib.parse import urlencode
from itertools import groupby
from random import shuffle, randint
from secret import HASH_PADDLE
import datetime
import hashlib
import json

from mangaki.choices import TOP_CATEGORY_CHOICES

POSTERS_PER_PAGE = 24
TITLES_PER_PAGE = 24
USERNAMES_PER_PAGE = 24
REFERENCE_DOMAINS = (
    ('http://myanimelist.net', 'myAnimeList'),
    ('http://animeka.com', 'Animeka'),
    ('http://vgmdb.net', 'VGMdb'),
    ('http://anidb.net', 'AniDB')
)

RATING_COLORS = {
    'favorite': {'normal': '#f8d549', 'highlight': '#f8d549'},
    'like': {'normal': '#5cb85c', 'highlight': '#47a447'},
    'neutral': {'normal': '#f0ad4e', 'highlight': '#ec971f'},
    'dislike': {'normal': '#d9534f', 'highlight': '#c9302c'},
    'willsee': {'normal': '#337ab7', 'highlight': '#286090'},
    'wontsee': {'normal': '#5bc0de', 'highlight': '#31b0d5'}
}

KIZU_ID = 13679
UTA_ID = 14293
KIZU_AP_ID = 9

def display_queries():
    for line in connection.queries:
        print(line['sql'][:100], line['time'])


def get_rated_works(user):
    rated_works = {}
    for work_id, choice in Rating.objects.filter(user=user).values_list('work_id', 'choice'):
        rated_works[work_id] = choice
    print(len(rated_works))
    return rated_works


def update_poster_if_nsfw(obj, user):
    if obj.nsfw and (not user.is_authenticated() or not user.profile.nsfw_ok):
        obj.poster = '/static/img/nsfw.jpg'  # NSFW


def update_poster_if_nsfw_dict(d, user):
    if d['nsfw'] and (not user.is_authenticated() or not user.profile.nsfw_ok):
        d['poster'] = '/static/img/nsfw.jpg'  # NSFW


def update_score_while_rating(user, work, choice):
    recommendations_list = Recommendation.objects.filter(target_user=user, work=work)
    for reco in recommendations_list:
        if choice == 'like':
            reco.user.profile.score += 1
        elif choice == 'favorite':
            reco.user.profile.score += 5
        if Rating.objects.filter(user=user, work=work, choice='like').count() > 0:
            reco.user.profile.score -= 1
        if Rating.objects.filter(user=user, work=work, choice='favorite').count() > 0:
            reco.user.profile.score -= 5
        Profile.objects.filter(user=reco.user).update(score=reco.user.profile.score)


def update_score_while_unrating(user, work, choice):
    recommendations_list = Recommendation.objects.filter(target_user=user, work=work)
    for reco in recommendations_list:
        if choice == 'like':
            reco.user.profile.score -= 1
            Profile.objects.filter(user=reco.user).update(score=reco.user.profile.score)
        elif choice == 'favorite':
            reco.user.profile.score -= 5
            Profile.objects.filter(user=reco.user).update(score=reco.user.profile.score)


class AnimeDetail(AjaxableResponseMixin, FormMixin, DetailView):
    queryset = Anime.objects.select_related('director', 'composer', 'author')
    form_class = SuggestionForm

    def get_success_url(self):
        return 'anime/%d' % self.object.pk

    def get_context_data(self, **kwargs):
        context = super(AnimeDetail, self).get_context_data(**kwargs)
        anime = self.object
        update_poster_if_nsfw(anime, self.request.user)
        context['object'].source = anime.source.split(',')[0]

        genres = []
        for genre in anime.genre.all():
            genres.append(genre.title)
        context['genres'] = ', '.join(genres)

        if self.request.user.is_authenticated():
            context['suggestion_form'] = SuggestionForm(instance=Suggestion(user=self.request.user, work=self.object))
            try:
                if Rating.objects.filter(user=self.request.user, work=anime, choice='favorite').count() > 0:
                    context['rating'] = 'favorite'
                else:
                    context['rating'] = anime.rating_set.get(user=self.request.user).choice
            except Rating.DoesNotExist:
                pass

        context['references'] = []
        for reference in anime.reference_set.all():
            for domain, name in REFERENCE_DOMAINS:
                if reference.url.startswith(domain):
                    context['references'].append((reference.url, name))

        nb = Counter(Rating.objects.filter(work=anime).values_list('choice', flat=True))
        labels = {'favorite': 'Ajoutés aux favoris', 'like': 'Ont aimé', 'neutral': 'Neutre', 'dislike': 'N\'ont pas aimé', 'willsee': 'Ont envie de voir', 'wontsee': 'N\'ont pas envie de voir'}
        seen_ratings = ['favorite', 'like', 'neutral', 'dislike']
        total = sum(nb.values())
        if total > 0:
            context['stats'] = []
            seen_total = sum(nb[rating] for rating in seen_ratings)
            for rating in labels:
                if seen_total > 0 and rating not in seen_ratings:
                    continue
                context['stats'].append({'value': nb[rating], 'colors': RATING_COLORS[rating], 'label': labels[rating]})
            context['seen_percent'] = round(100 * seen_total / float(total))

        anime_events = anime.event_set.filter(date__gte=timezone.now())
        if anime_events.count() > 0:
            my_events = {}
            if self.request.user.is_authenticated():
                my_events = dict(self.request.user.attendee_set.filter(
                    event__in=anime_events).values_list('event_id', 'attending'))

            context['events'] = [
                {
                    'id': event.id,
                    'attending': my_events.get(event.id, None),
                    'type': event.get_event_type_display(),
                    'channel': event.channel,
                    'date': event.get_date(),
                    'link': event.link,
                    'location': event.location,
                    'nb_attendees': event.attendee_set.filter(attending=True).count(),
                } for event in anime_events
            ]
            
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.save()
        return super(AnimeDetail, self).form_valid(form)


class MangaDetail(AjaxableResponseMixin, FormMixin, DetailView):
    model = Manga
    form_class = SuggestionForm

    def get_success_url(self):
        return 'manga/%d' % self.object.pk

    def get_context_data(self, **kwargs):
        context = super(MangaDetail, self).get_context_data(**kwargs)
        update_poster_if_nsfw(self.object, self.request.user)
        print(self.object.poster)
        context['object'].source = context['object'].source.split(',')[0]

        genres = []
        for genre in context['object'].genre.all():
            genres.append(genre.title)
        context['genres'] = ', '.join(genres)

        if self.request.user.is_authenticated():
            context['suggestion_form'] = SuggestionForm(instance=Suggestion(user=self.request.user, work=self.object))
            try:
                if Rating.objects.filter(user=self.request.user, work=self.object, choice='favorite').count() > 0:
                    context['rating'] = 'favorite'
                else:
                    context['rating'] = self.object.rating_set.get(user=self.request.user).choice
            except Rating.DoesNotExist:
                pass
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.save()
        return super(MangaDetail, self).form_valid(form)


class AlbumDetail(AjaxableResponseMixin, FormMixin, DetailView):
    model = Album
    form_class = SuggestionForm

    def get_success_url(self):
        return 'album/%d' % self.object.pk

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        update_poster_if_nsfw(self.object, self.request.user)
        print(self.object.poster)
        context['object'].source = context['object'].source.split(',')[0]

        genres = []
        if self.request.user.is_authenticated():
            context['suggestion_form'] = SuggestionForm(instance=Suggestion(user=self.request.user, work=self.object))
            try:
                if Rating.objects.filter(user=self.request.user, work=self.object, choice='favorite').count() > 0:
                    context['rating'] = 'favorite'
                else:
                    context['rating'] = self.object.rating_set.get(user=self.request.user).choice
            except Rating.DoesNotExist:
                pass
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return HttpResponseForbidden()
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.save()
        return super().form_valid(form)


class EventDetail(LoginRequiredMixin, DetailView):
    model = Event

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'next' in request.GET:
            return redirect(request.GET['next'])
        return redirect(reverse('anime-detail', args=(self.object.anime_id,)))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        attending = None
        if 'wontgo' in request.POST:
            attending = False
        if 'willgo' in request.POST:
            attending = True
        if attending is not None:
            Attendee.objects.update_or_create(
                event=self.object, user=request.user,
                defaults={'attending': attending })
        elif 'cancel' in request.POST:
            Attendee.objects.filter(event=self.object, user=request.user).delete()
        return redirect(request.GET['next']);

def controversy(nb_likes, nb_dislikes):
    if nb_likes == 0 or nb_dislikes == 0:
        return 0
    return (nb_likes + nb_dislikes) ** min(float(nb_likes) / nb_dislikes, float(nb_dislikes) / nb_likes)


def get_scores(bundle, ranking='controversy'):
    ratings = Rating.objects.filter(work__in=bundle).values('work', 'choice').annotate(count=Count('pk')).order_by('work', 'choice')
    score = {}
    for work_id, ratings in groupby(ratings, lambda rating: rating['work']):
        nb_likes = nb_dislikes = 0
        for rating in ratings:
            if rating['choice'] == 'like':
                nb_likes = rating['count']
            elif rating['choice'] == 'dislike':
                nb_dislikes = rating['count']
        if ranking == 'controversy':
            score[work_id] = controversy(nb_likes, nb_dislikes)
        elif ranking == 'top':
            score[work_id] = nb_likes if nb_dislikes <= 20 else 0
        elif ranking == 'random':  # Perles au hasard
            score[work_id] = randint(1, 42) if nb_dislikes <= 5 and nb_likes >= 3 else 0
    return score


def get_bundle(category, sort_mode, my_rated_works={}):
    already_rated = ', '.join(map(str, my_rated_works.keys())) if my_rated_works.keys() else '0'
    work_query = 'SELECT mangaki_{category}.work_ptr_id, mangaki_work.id, mangaki_work.title, mangaki_work.poster, mangaki_work.nsfw, COUNT(mangaki_work.id) rating_count FROM mangaki_{category}, mangaki_work, mangaki_rating WHERE mangaki_{category}.work_ptr_id = mangaki_work.id AND mangaki_rating.work_id = mangaki_work.id AND (mangaki_{category}.work_ptr_id NOT IN (' + already_rated + ')) GROUP BY mangaki_work.id, mangaki_{category}.work_ptr_id HAVING COUNT(mangaki_work.id) >= {min_ratings} ORDER BY {order_by}'
    # work_query = 'SELECT mangaki_{category}.work_ptr_id, mangaki_work.id, mangaki_work.title, mangaki_work.poster, mangaki_work.nsfw, COUNT(mangaki_work.id) rating_count FROM mangaki_{category}, mangaki_work, mangaki_rating WHERE mangaki_{category}.work_ptr_id = mangaki_work.id AND mangaki_rating.work_id = mangaki_work.id AND (mangaki_{category}.work_ptr_id NOT IN (' + already_rated + ')) GROUP BY mangaki_work.id, mangaki_{category}.work_ptr_id HAVING COUNT(mangaki_work.id) >= {min_ratings} ORDER BY {order_by}'
    if category == 'anime':
        obj = Anime.objects
    elif category == 'manga':
        obj = Manga.objects
    # Work.objects.in_bulk(
    # return Work.objects.in_bulk(Deck.objects.get(category=category, sort_mode=sort_mode).content.split(','))
    if sort_mode == 'popularity':
        return obj.raw(work_query.format(category=category, min_ratings=6 if category == 'anime' else 0, order_by='rating_count DESC'))
    elif sort_mode == 'top':
        return obj.raw(work_query.format(category=category, min_ratings=100 if category == 'anime' else 1, order_by='rating_count DESC'))
    elif sort_mode == 'controversy' or sort_mode == 'random':
        return obj.raw(work_query.format(category=category, min_ratings=6 if category == 'anime' else 1, order_by='rating_count DESC'))
    else:
        return obj.raw(work_query.format(category=category, min_ratings=1 if category == 'anime' else 0, order_by='title'))


def filter_deck(deck, my_rated_works, deja_vu):
    works = [work_id for work_id in deck if int(work_id) not in my_rated_works and work_id not in deja_vu]
    return works[:54]


def get_card(request, category, sort_id=1):
    chrono = Chrono(True)
    deja_vu = request.GET.get('dejavu', '').split(',')
    sort_mode = ['popularity', 'controversy', 'top', 'random'][int(sort_id) - 1]
    my_rated_works = get_rated_works(request.user) if request.user.is_authenticated() else {}
    chrono.save('got rated works')
    if Deck.objects.filter(category=category, sort_mode=sort_mode):
        deck = Deck.objects.get(category=category, sort_mode=sort_mode).content.split(',')
    else:  # Temporary data
        if category == 'anime':
            bundle = Anime.objects.all()
        elif category == 'manga':
            bundle = Manga.objects.all()
        deck = [str(work.id) for work in bundle]
        Deck(category=category, sort_mode=sort_mode, content=','.join(deck)).save()
    filtered_deck = filter_deck(deck, my_rated_works, deja_vu)
    chrono.save('filter deck')
    data = {}
    for work_id, title, poster, synopsis, nsfw in Work.objects.filter(id__in=filtered_deck).values_list('id', 'title', 'poster', 'synopsis', 'nsfw'):
        data[work_id] = {'title': title, 'poster': poster, 'synopsis': synopsis, 'nsfw': nsfw}
    # display_queries()
    cards = []
    for work_id in filtered_deck:
        work = data[int(work_id)]
        update_poster_if_nsfw_dict(work, request.user)
        card = {'id': work_id, 'title': work['title'], 'poster': work['poster'], 'category': category, 'synopsis': work['synopsis']}
        cards.append(card)
    # return render(request, 'about.html')
    return HttpResponse(json.dumps(cards), content_type='application/json')


class AnimeList(ListView):
    model = Anime
    context_object_name = 'anime'

    def get_queryset(self):
        bundle = Anime.objects.none()
        artist_id = self.kwargs.get('artist_id')
        if artist_id:
            artist = Artist.objects.get(id=artist_id)
            bundle = artist.authored.all() | artist.directed.all() | artist.composed.all()
            return bundle.order_by('title')
        letter = self.request.GET.get('letter', '')
        if letter:
            bundle = Anime.objects.all().order_by('title')
            if letter == '0':  # '#'
                bundle = bundle.exclude(title__regex=r'^[a-zA-Z]')
            else:
                bundle = bundle.filter(title__istartswith=letter)
        return bundle

    def get_context_data(self, **kwargs):
        my_rated_works = get_rated_works(self.request.user) if self.request.user.is_authenticated() else {}
        artist_id = self.kwargs.get('artist_id')
        sort_mode = self.request.GET.get('sort', 'mosaic')
        flat_mode = self.request.GET.get('flat', '0')
        letter = self.request.GET.get('letter', '')
        page = int(self.request.GET.get('page', '1'))
        context = super(AnimeList, self).get_context_data(**kwargs)

        if artist_id:
            sort_mode = 'alpha'
            context['artist'] = Artist.objects.get(id=artist_id)
        if sort_mode == 'mosaic':
            anime_ids = []
            context['object_list'] = [Work(title='Chargement…', poster='/static/img/chiro.gif') for _ in range(4)]
        elif sort_mode in ['popularity', 'controversy', 'top', 'random']:
            anime_ids = Deck.objects.get(category='anime', sort_mode=sort_mode).content.split(',')
            if sort_mode == 'random':
                shuffle(anime_ids)
        else:
            anime_ids = list(map(lambda obj: obj.id, context['object_list']))  # Double conversion, to fix

        paginator = Paginator(anime_ids, TITLES_PER_PAGE if flat_mode == '1' else POSTERS_PER_PAGE)

        try:
            page_anime_ids = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            page_anime_ids = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            page_anime_ids = paginator.page(paginator.num_pages)

        context['params'] = {'sort': sort_mode, 'letter': letter, 'page': page, 'flat': flat_mode}
        context['url'] = urlencode({'sort': sort_mode, 'letter': letter})
        context['anime_count'] = Anime.objects.count()
        context['pages'] = filter(lambda x: 1 <= x <= paginator.num_pages, range(page_anime_ids.number - 2, page_anime_ids.number + 2 + 1))
        context['template_mode'] = 'work_no_poster.html' if flat_mode == '1' else 'work_poster.html'

        works = Work.objects.in_bulk(page_anime_ids)
        anime_list = list(map(lambda work_id: works[int(work_id)], page_anime_ids))
        for obj in anime_list:
            update_poster_if_nsfw(obj, self.request.user)
            if self.request.user.is_authenticated():
                obj.rating = my_rated_works.get(obj.id, None)  # Necessary for displaying current ratings on AnimeList
        if sort_mode != 'mosaic':
            context['object_list'] = anime_list
        return context


class MangaList(ListView):
    model = Manga
    context_object_name = 'manga'

    def get_queryset(self):
        bundle = Manga.objects.none()
        letter = self.request.GET.get('letter', '')
        if letter:
            bundle = Manga.objects.all().order_by('title')
            if letter == '0':  # '#'
                bundle = bundle.exclude(title__regex=r'^[a-zA-Z]')
            else:
                bundle = bundle.filter(title__istartswith=letter)
        return bundle

    def get_context_data(self, **kwargs):
        my_rated_works = get_rated_works(self.request.user) if self.request.user.is_authenticated() else {}
        sort_mode = self.request.GET.get('sort', 'mosaic')
        flat_mode = self.request.GET.get('flat', '0')
        letter = self.request.GET.get('letter', '')
        page = int(self.request.GET.get('page', '1'))
        context = super(MangaList, self).get_context_data(**kwargs)

        # context['object_list'] = list(context['object_list'])
        if sort_mode == 'mosaic':
            manga_ids = []
            context['object_list'] = [Work(title='Chargement…', poster='/static/img/chiro.gif') for _ in range(4)]
        elif sort_mode in ['popularity', 'controversy', 'top', 'random']:
            manga_ids = Deck.objects.get(category='manga', sort_mode=sort_mode).content.split(',')
            if sort_mode == 'random':
                shuffle(manga_ids)
        else:
            manga_ids = list(map(lambda obj: obj.id, context['object_list']))  # Double conversion (and repetition), to fix  

        paginator = Paginator(manga_ids, TITLES_PER_PAGE if flat_mode == '1' else POSTERS_PER_PAGE)

        try:
            page_manga_ids = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            page_manga_ids = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            page_manga_ids = paginator.page(paginator.num_pages)

        context['params'] = {'sort': sort_mode, 'letter': letter, 'page': page, 'flat': flat_mode}
        context['url'] = urlencode({'sort': sort_mode, 'letter': letter})
        context['manga_count'] = Manga.objects.count()
        context['pages'] = filter(lambda x: 1 <= x <= paginator.num_pages, range(page_manga_ids.number - 2, page_manga_ids.number + 2 + 1))
        context['template_mode'] = 'work_no_poster.html' if flat_mode == '1' else 'work_poster.html'

        works = Work.objects.in_bulk(page_manga_ids)
        manga_list = list(map(lambda work_id: works[int(work_id)], page_manga_ids))
        for obj in manga_list:
            update_poster_if_nsfw(obj, self.request.user)
            if self.request.user.is_authenticated():
                obj.rating = my_rated_works.get(obj.id, None)
        if sort_mode != 'mosaic':
            context['object_list'] = manga_list
        return context


class UserList(ListView):
    model = User
    # context_object_name = 'anime'

    def get_queryset(self):
        bundle = User.objects.filter(profile__is_shared=True).order_by('-id')
        letter = self.request.GET.get('letter', '')
        if letter:
            if letter == '0':  # '#'
                bundle = bundle.exclude(username__regex=r'^[a-zA-Z]').order_by('username')
            else:
                bundle = bundle.filter(username__istartswith=letter).order_by('username')
        return bundle

    def get_context_data(self, **kwargs):
        context = super(UserList, self).get_context_data(**kwargs)

        letter = self.request.GET.get('letter', '')
        page = int(self.request.GET.get('page', '1'))
        context['object_list'] = list(context['object_list'])
        paginator = Paginator(context['object_list'], USERNAMES_PER_PAGE)
        try:
            user_list = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            user_list = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            user_list = paginator.page(paginator.num_pages)
        context['params'] = {'letter': letter, 'page': page}
        context['url'] = urlencode({'letter': letter})
        context['pages'] = filter(lambda x: 1 <= x <= paginator.num_pages, range(user_list.number - 2, user_list.number + 2 + 1))
        context['object_list'] = user_list

        context['trio_elm'] = User.objects.filter(username__in=['jj', 'Lily', 'Sedeto'])
        return context


def get_profile(request, username):
    chrono = Chrono(True)
    try:
        is_shared = Profile.objects.get(user__username=username).is_shared
    except Profile.DoesNotExist:
        Profile(user=request.user).save()  # À supprimer à terme # Tu parles, maintenant ça va être encore plus compliqué
        is_shared = True
    # chrono.save('get profile')
    user = User.objects.get(username=username)
    category = request.GET.get('category', 'anime')
    ordering = ['favorite', 'willsee', 'like', 'neutral', 'dislike', 'wontsee']
    seen_anime_list = []
    unseen_anime_list = []
    seen_manga_list = []
    unseen_manga_list = []
    c = 0
    """for work_id, work_title, is_anime, choice in Rating.objects.filter(user__username=username).select_related('work', 'work__anime', 'work__manga').values_list('work_id', 'work__title', 'work__anime', 'choice'):
        # print(work_id, work_title, is_anime, choice)
        seen = choice in ['favorite', 'like', 'neutral', 'dislike']
        rating = {'work': {'id': work_id, 'title': work_title}, 'choice': choice}
        # print(rating)
        if is_anime:
            if seen:
                seen_anime_list.append(rating)
            else:
                unseen_anime_list.append(rating)
        else:
            if seen:
                seen_manga_list.append(rating)
            else:
                unseen_manga_list.append(rating)
        c += 1
        if c >= 200:
            break"""
    rating_list = sorted(Rating.objects.filter(user__username=username).select_related('work', 'work__anime', 'work__manga'), key=lambda x: (ordering.index(x.choice), x.work.title))  # Tri par note puis nom
    # , key=lambda x: (ordering.index(x['choice']), 1))  # Tri par note puis nom
    # print(rating_list[:5])
    # chrono.save('get ratings %d queries' % len(connection.queries))

    received_recommendation_list = []
    sent_recommendation_list = []
    if category == 'recommendation':
        received_recommendations = Recommendation.objects.filter(target_user__username=username)
        sent_recommendations = Recommendation.objects.filter(user__username=username)
        for reco in received_recommendations:
            try:
                reco.work.anime
                if Rating.objects.filter(work=reco.work, user__username=username, choice__in=['favorite', 'like', 'neutral', 'dislike']).count() == 0:
                    received_recommendation_list.append({'category': 'anime', 'id': reco.work.id, 'title': reco.work.title, 'username': reco.user.username})
            except Anime.DoesNotExist:
                if Rating.objects.filter(work=reco.work, user__username=username, choice__in=['favorite', 'like', 'neutral', 'dislike']).count() == 0:
                    received_recommendation_list.append({'category': 'manga', 'id': reco.work.id, 'title': reco.work.title, 'username': reco.user.username})
        for reco in sent_recommendations:
            try:
                reco.work.anime
                if Rating.objects.filter(work=reco.work, user=reco.target_user, choice__in=['favorite', 'like', 'neutral', 'dislike']).count() == 0:
                    sent_recommendation_list.append({'category': 'anime', 'id': reco.work.id, 'title': reco.work.title, 'username': reco.target_user.username})
            except Anime.DoesNotExist:
                if Rating.objects.filter(work=reco.work, user=reco.target_user, choice__in=['favorite', 'like', 'neutral', 'dislike']).count() == 0:
                    sent_recommendation_list.append({'category': 'manga', 'id': reco.work.id, 'title': reco.work.title, 'username': reco.target_user.username})
    # chrono.save('get reco %d queries' % len(connection.queries))

    for r in rating_list:
        seen = r.choice in ['favorite', 'like', 'neutral', 'dislike']
        rating = r#{'work': {'id': r.work.id, 'title': r.work.title}, 'choice': r.choice}
        try:
            r.work.anime
            if seen:
                seen_anime_list.append(rating)
            else:
                unseen_anime_list.append(rating)
        except Anime.DoesNotExist:
            if seen:
                seen_manga_list.append(rating)
            else:
                unseen_manga_list.append(rating)
    # chrono.save('categorize ratings')
    member_time = datetime.datetime.now().replace(tzinfo=utc) - user.date_joined
    seen_list = seen_anime_list if category == 'anime' else seen_manga_list
    unseen_list = unseen_anime_list if category == 'anime' else unseen_manga_list

    # Events
    events = [
        {
            'id': attendee.event_id,
            'anime_id': attendee.event.anime_id,
            'attending': True,
            'type': attendee.event.get_event_type_display(),
            'channel': attendee.event.channel,
            'date': attendee.event.get_date(),
            'link': attendee.event.link,
            'location': attendee.event.location,
            'title': attendee.event.anime.title,
        } for attendee in user.attendee_set.filter(event__date__gte=timezone.now()).select_related('event', 'event__anime__title')
    ]

    data = {
        'username': username,
        'score': user.profile.score,
        'is_shared': is_shared,
        'category': category,
        'avatar_url': user.profile.get_avatar_url(),
        'member_days': member_time.days,
        'anime_count': len(seen_anime_list),
        'manga_count': len(seen_manga_list),
        'reco_count': len(received_recommendation_list),
        'seen_list': seen_list if is_shared else [],
        'unseen_list': unseen_list if is_shared else [],
        'received_recommendation_list': received_recommendation_list if is_shared else [],
        'sent_recommendation_list': sent_recommendation_list if is_shared else [],
    }
    for key in data:
        try:
            print(key, len(data[key]))
        except:
            print(key, '->', data[key])
    chrono.save('get request')
    return render(request, 'profile.html', {
        'username': username,
        'score': user.profile.score,
        'is_shared': is_shared,
        'category': category,
        'avatar_url': user.profile.get_avatar_url(),
        'member_days': member_time.days,
        'anime_count': len(seen_anime_list),
        'manga_count': len(seen_manga_list),
        'reco_count': len(received_recommendation_list),
        'seen_list': seen_list if is_shared else [],
        'unseen_list': unseen_list if is_shared else [],
        'received_recommendation_list': received_recommendation_list if is_shared else [],
        'sent_recommendation_list': sent_recommendation_list if is_shared else [],
        'events': events,
    })


def index(request):
    if request.user.is_authenticated():
        if Rating.objects.filter(user=request.user).count() == 0:
            return redirect('/anime/')
    # texte = Announcement.objects.get(title='Flash News').text
    # context = {'annonce': texte}
    partners = Partner.objects.filter()
    kizu_rating = None
    uta_rating = None
    if request.user.is_authenticated():
        for rating in Rating.objects.filter(work_id__in=[KIZU_ID, UTA_ID], user=request.user):
            if rating.work_id == KIZU_ID:
                kizu_rating = rating.choice
            elif rating.work_id == UTA_ID:
                uta_rating = rating.choice
    return render(request, 'index.html', {
        'partners': partners,
        'kizumonogatari': Anime.objects.get(pk=KIZU_ID),
        'utamonogatari': Album.objects.get(pk=UTA_ID),
        'kizumonogatari_rating': kizu_rating,
        'utamonogatari_rating': uta_rating,
    })


def about(request):
    return render(request, 'about.html')


def events(request):
    kizu_rating = None
    uta_rating = None
    ap_attending = None
    if request.user.is_authenticated():
        for rating in Rating.objects.filter(work_id__in=[KIZU_ID, UTA_ID], user=request.user):
            if rating.work_id == KIZU_ID:
                kizu_rating = rating.choice
            elif rating.work_id == UTA_ID:
                uta_rating = rating.choice
        for attendee in Attendee.objects.filter(event_id=KIZU_AP_ID, user=request.user):
            ap_attending = attendee.attending
    return render(
        request, 'events.html',
        {
            'screenings': Event.objects.filter(event_type='screening', date__gte=timezone.now()),
            'kizumonogatari': Anime.objects.get(pk=KIZU_ID),
            'utamonogatari': Album.objects.get(pk=UTA_ID),
            'wakanim': Partner.objects.get(pk=12),
            'kizumonogatari_rating': kizu_rating,
            'utamonogatari_rating': uta_rating,
            'kizu_ap': {
                'id': KIZU_AP_ID,
                'attending': ap_attending,
            },
        })

def top(request, category_slug):
    categories = dict(TOP_CATEGORY_CHOICES)
    if category_slug not in categories:
        raise Http404
    try:
        top = Top.objects.filter(category=category_slug).latest('date')
    except Top.DoesNotExist:
        raise Http404
    data = []
    rankings = Ranking.objects.filter(top=top).prefetch_related('content_object')
    for rank, ranking in enumerate(rankings):
        data.append({
            'rank': rank + 1,
            'id': ranking.object_id,
            'name': str(ranking.content_object),
            'score': ranking.score,
            'nb_ratings': ranking.nb_ratings,
            'nb_stars': ranking.nb_stars,
        })
    return render(request, 'top.html', {
        'date': top.date,
        'size': len(data),
        'category_slug': category_slug,
        'category': categories[category_slug].lower(),
        'top': data,
    })


def rate_work(request, work_id):
    if request.user.is_authenticated() and request.method == 'POST':
        work = get_object_or_404(Work, id=work_id)
        choice = request.POST.get('choice', '')
        if choice not in ['like', 'neutral', 'dislike', 'willsee', 'wontsee', 'favorite']:
            return HttpResponse()
        if Rating.objects.filter(user=request.user, work=work, choice=choice).count() > 0:
            Rating.objects.filter(user=request.user, work=work, choice=choice).delete()
            update_score_while_unrating(request.user, work, choice)
            return HttpResponse('none')
        update_score_while_rating(request.user, work, choice)
        Rating.objects.update_or_create(user=request.user, work=work, defaults={'choice': choice})
        return HttpResponse(choice)
    return HttpResponse()


def recommend_work(request, work_id, target_id):
    if request.user.is_authenticated() and request.method == 'POST':
        work = get_object_or_404(Work, id=work_id)
        target_user = get_object_or_404(User, id=target_id)
        if target_user == request.user:
            return HttpResponse('nonsense')
        if Recommendation.objects.filter(user=request.user, work=work, target_user=target_user).count() > 0:
            return HttpResponse('double')
        if not Rating.objects.filter(user=target_user, work=work, choice__in=['favorite', 'like', 'neutral', 'dislike']):
            Recommendation.objects.update_or_create(user=request.user, work=work, target_user=target_user)
            return HttpResponse('success')
    return HttpResponse()


def get_users(request, query=''):
    data = []
    for user in User.objects.all() if not query else User.objects.filter(username__icontains=query):
        data.append({'id': user.id, 'username': user.username, 'tokens': user.username.lower().split()})
    return HttpResponse(json.dumps(data), content_type='application/json')


def get_user_for_recommendations(request, work_id, query=''):
    data = []
    for user in User.objects.all() if not query else User.objects.filter(username__icontains=query):
        data.append({'id': user.id, 'username': user.username, 'work_id': work_id, 'tokens': user.username.lower().split()})
    return HttpResponse(json.dumps(data), content_type='application/json')


class MarkdownView(DetailView):
    model = Page
    slug_field = 'name'
    template_name = 'static.html'

    def get_context_data(self, **kwargs):
        page = super(MarkdownView, self).get_object()
        return {'html': markdown(page.markdown)}


def get_works(request, category, query=''):
    if category == 'anime':
        data = []
        for anime in Anime.objects.all() if not query else Anime.objects.filter(title__icontains=query):
            data.append({'id': anime.id, 'description': anime.synopsis[:50] + '…', 'value': anime.title, 'tokens': anime.title.lower().split(), 'year': '' if not anime.date else anime.date.year})
        return HttpResponse(json.dumps(data), content_type='application/json')
    else:
        data = []
        for manga in Manga.objects.all() if not query else Manga.objects.filter(title__icontains=query):
            data.append({'id': manga.id, 'description': manga.synopsis[:50] + '…', 'value': manga.title, 'tokens': manga.title.lower().split(), 'year': '' if not manga.date else manga.date.year})
        return HttpResponse(json.dumps(data), content_type='application/json')
    return HttpResponse()


def get_extra_anime(request, query):
    entries = lookup_mal_api(query)
    retrieve_anime(entries)
    return get_works(request, 'anime', query)


def get_extra_manga(request, query):
    SearchIssue(user=request.user, title=query).save()
    return HttpResponse()


def get_reco_list(request, category, editor):
    reco_list = []
    for work, is_manga, in_willsee in get_recommendations(request.user, category, editor):
        update_poster_if_nsfw(work, request.user)
        reco_list.append({'id': work.id, 'title': work.title, 'poster': work.poster, 'synopsis': work.synopsis,
            'category': 'manga' if is_manga else 'anime', 'rating': 'willsee' if in_willsee else 'None'})
    return HttpResponse(json.dumps(reco_list), content_type='application/json')


def remove_reco(request, work_id, username, targetname):
    work = get_object_or_404(Work, id=work_id)
    user = get_object_or_404(User, username=username)
    target = get_object_or_404(User, username=targetname)
    if Rating.objects.filter(user=target, work=work, choice__in=['favorite', 'like', 'neutral', 'dislike']).count() == 0 and (request.user == user or request.user == target):
        Recommendation.objects.get(work=work, user=user, target_user=target).delete()


def remove_all_reco(request, targetname):
    target = get_object_or_404(User, username=targetname)
    if target == request.user:
        reco_list = Recommendation.objects.filter(target_user=target)
        for reco in reco_list:
            if Rating.objects.filter(user=request.user, work=reco.work, choice__in=['favorite', 'like', 'neutral', 'dislike']).count() == 0:
                reco.delete()


@login_required
def get_reco(request):
    category = request.GET.get('category', 'all')
    editor = request.GET.get('editor', 'unspecified')
    reco_list = []
    dummy = Work(title='Chargement…', poster='/static/img/chiro.gif')
    for _ in range(4):
        reco_list.append((dummy, 'dummy'))
    return render(request, 'mangaki/reco_list.html', {'reco_list': reco_list, 'category': category, 'editor': editor})


def update_shared(request):
    if request.user.is_authenticated() and request.method == 'POST':
        Profile.objects.filter(user=request.user).update(is_shared=request.POST['is_shared'] == 'true')
    return HttpResponse()


def update_nsfw(request):
    if request.user.is_authenticated() and request.method == 'POST':
        Profile.objects.filter(user=request.user).update(nsfw_ok=request.POST['nsfw_ok'] == 'true')
    return HttpResponse()


def update_newsletter(request):
    if request.user.is_authenticated() and request.method == 'POST':
        Profile.objects.filter(user=request.user).update(newsletter_ok=request.POST['newsletter_ok'] == 'true')
    return HttpResponse()


def update_reco_willsee(request):
    if request.user.is_authenticated() and request.method == 'POST':
        Profile.objects.filter(user=request.user).update(reco_willsee_ok=request.POST['reco_willsee_ok'] == 'true')
    return HttpResponse()


def import_from_mal(request, mal_username):
    if request.method == 'POST':
        nb_added, fails = import_mal(mal_username, request.user.username)
        return HttpResponse('%d added; %d fails: %s' % (nb_added, len(fails), '\n'.join(fails)))
    return HttpResponse()


def report_nsfw(request, pk):
    Anime.objects.filter(id=pk).update(nsfw=True)
    return redirect('/anime/%s' % pk)


def add_pairing(request, artist_id, work_id):
    if request.user.is_authenticated():
        artist = get_object_or_404(Artist, id=artist_id)
        work = get_object_or_404(Work, id=work_id)
        Pairing(user=request.user, artist=artist, work=work).save()
    return HttpResponse()


@receiver(user_signed_up)
@receiver(social_account_added)
def register_profile(sender, **kwargs):
    user = kwargs['user']
    Profile(user=user).save()


def unsubscribe(request, pk, key):
    user = User.objects.get(id=pk)
    if user and hashlib.md5(bytes(user.username + HASH_PADDLE, 'utf-8')).hexdigest() == key:
        Profile.objects.filter(user=user).update(newsletter_ok=False)
        return HttpResponse('Vous êtes bien désinscrit. À bientôt sur <a href="http://mangaki.fr">http://mangaki.fr</a> :)')
    return HttpResponse()
