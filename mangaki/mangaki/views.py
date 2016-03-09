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
from mangaki.models import Work, Anime, Manga, Album, Rating, Page, Profile, Artist, Suggestion, SearchIssue, Announcement, Recommendation, Pairing, Top, Ranking
from mangaki.mixins import AjaxableResponseMixin
from mangaki.forms import SuggestionForm
from mangaki.utils.mal import lookup_mal_api, import_mal, retrieve_anime
from mangaki.utils.recommendations import get_recommendations
from mangaki.utils.chrono import Chrono
from irl.models import Event, Partner, Attendee

from collections import Counter
from markdown import markdown
from urllib.parse import urlencode
from random import shuffle, randint
from secret import HASH_PADDLE
import datetime
import hashlib
import json

from mangaki.choices import TOP_CATEGORY_CHOICES

from natsort import natsorted

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

GHIBLI_IDS = [2591, 8153, 2461, 53, 958, 30, 1563, 410, 60, 3315, 3177, 106]

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
        context['object'].source = context['object'].source.split(',')[0]

        genres = []
        if self.request.user.is_authenticated():
            context['suggestion_form'] = SuggestionForm(instance=Suggestion(user=self.request.user, work=self.object))
            try:
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


def get_card(request, category, sort_id=1):
    chrono = Chrono(True)
    deja_vu = request.GET.get('dejavu', '').split(',')
    sort_mode = ['popularity', 'controversy', 'top', 'random'][int(sort_id) - 1]
    queryset = Work.objects.filter(category__slug=category)
    if sort_mode == 'popularity':
        queryset = queryset.popular()
    elif sort_mode == 'controversy':
        queryset = queryset.controversial()
    elif sort_mode == 'top':
        queryset = queryset.top()
    else:
        queryset = queryset.random().order_by('?')
    if request.user.is_authenticated():
        rated_works = Rating.objects.filter(user=request.user).values('work_id')
        queryset = queryset.exclude(id__in=rated_works)
    queryset = queryset[:54]
    cards = []
    for work in queryset.values('id', 'title', 'poster', 'synopsis', 'nsfw'):
        update_poster_if_nsfw_dict(work, request.user)
        work['category'] = category
        cards.append(work)

    return HttpResponse(json.dumps(cards), content_type='application/json')


class AnimeList(ListView):
    template_name = 'mangaki/anime_list.html'
    context_object_name = 'anime'
    paginate_by = POSTERS_PER_PAGE

    def get_queryset(self):
        artist_id = self.kwargs.get('artist_id')
        if artist_id:
            artist = Artist.objects.get(id=artist_id)
            bundle = artist.authored.all() | artist.directed.all() | artist.composed.all()
            return bundle.order_by('title')

        sort_mode = self.request.GET.get('sort', 'mosaic')

        bundle = Work.objects.filter(category__slug='anime')
        if sort_mode == 'top':
            return bundle.top()
        elif sort_mode == 'popularity':
            return bundle.popular()
        elif sort_mode == 'controversy':
            return bundle.controversial()
        elif sort_mode == 'random':
            return bundle.random().order_by('?')[:self.paginate_by]
        elif sort_mode == 'alpha':
            letter = self.request.GET.get('letter', '')
            if letter:
                if letter == '0':  # '#'
                    bundle = bundle.exclude(title__regex=r'^[a-zA-Z]')
                else:
                    bundle = bundle.filter(title__istartswith=letter)
            return bundle.order_by('title')

        return Work.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        artist_id = self.kwargs.get('artist_id')
        sort_mode = self.request.GET.get('sort', 'mosaic')
        flat_mode = self.request.GET.get('flat', '0')
        letter = self.request.GET.get('letter', '')

        if artist_id:
            sort_mode = 'alpha'
            context['artist'] = Artist.objects.get(id=artist_id)

        context['params'] = {'sort': sort_mode, 'letter': letter, 'flat': flat_mode}
        context['url'] = urlencode({'sort': sort_mode, 'letter': letter})
        context['anime_count'] = Anime.objects.count()
        context['template_mode'] = 'work_no_poster.html' if flat_mode == '1' else 'work_poster.html'

        if self.request.user.is_authenticated():
            ratings = dict(
                Rating.objects.filter(
                    user=self.request.user,
                    work__in=list(context['object_list'])) \
                .values_list('work_id', 'choice'))
        else:
            ratings = {}

        for obj in context['object_list']:
            obj.rating = ratings.get(obj.id, None)
            obj.poster = obj.safe_poster(self.request.user)

        if sort_mode == 'mosaic':
            context['object_list'] = [Work(title='Chargement…', poster='/static/img/chiro.gif') for _ in range(4)]

        return context


class MangaList(ListView):
    template_name = 'mangaki/manga_list.html'
    context_object_name = 'manga'
    paginate_by = POSTERS_PER_PAGE

    def get_queryset(self):
        sort_mode = self.request.GET.get('sort', 'mosaic')

        bundle = Work.objects.filter(category__slug='manga')
        if sort_mode == 'top':
            return bundle.top()
        elif sort_mode == 'popularity':
            return bundle.popular()
        elif sort_mode == 'controversy':
            return bundle.controversial()
        elif sort_mode == 'random':
            return bundle.random().order_by('?')[:self.paginate_by]
        elif sort_mode == 'alpha':
            letter = self.request.GET.get('letter', '')
            if letter:
                if letter == '0':  # '#'
                    bundle = bundle.exclude(title__regex=r'^[a-zA-Z]')
                else:
                    bundle = bundle.filter(title__istartswith=letter)
            return bundle.order_by('title')

        return Work.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sort_mode = self.request.GET.get('sort', 'mosaic')
        flat_mode = self.request.GET.get('flat', '0')
        letter = self.request.GET.get('letter', '')

        context['params'] = {'sort': sort_mode, 'letter': letter, 'flat': flat_mode}
        context['url'] = urlencode({'sort': sort_mode, 'letter': letter})
        context['manga_count'] = Manga.objects.count()
        context['template_mode'] = 'work_no_poster.html' if flat_mode == '1' else 'work_poster.html'

        if self.request.user.is_authenticated():
            ratings = dict(
                Rating.objects.filter(
                    user=self.request.user,
                    work__in=list(context['object_list'])) \
                .values_list('work_id', 'choice'))
        else:
            ratings = {}

        for obj in context['object_list']:
            obj.rating = ratings.get(obj.id, None)
            obj.poster = obj.safe_poster(self.request.user)

        if sort_mode == 'mosaic':
            context['object_list'] = [Work(title='Chargement…', poster='/static/img/chiro.gif') for _ in range(4)]

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
    rating_list = natsorted(Rating.objects.filter(user__username=username).select_related('work', 'work__anime', 'work__manga'), key=lambda x: (ordering.index(x.choice), x.work.title.lower()))  # Tri par note puis nom
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
        } for attendee in user.attendee_set.filter(event__date__gte=timezone.now(), attending=True).select_related('event', 'event__anime__title')
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
    ghibli_works = Anime.objects.in_bulk(GHIBLI_IDS)
    if request.user.is_authenticated():
        ghibli_ratings = dict(Rating.objects.filter(user=request.user, work_id__in=GHIBLI_IDS).values_list('work_id', 'choice'))
    else:
        ghibli_ratings = {}
    return render(
        request, 'events.html',
        {
            'screenings': Event.objects.filter(event_type='screening', date__gte=timezone.now()),
            'ghibli': [(ghibli_works[work_id], ghibli_ratings.get(work_id)) for work_id in GHIBLI_IDS],
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


def get_works(request, category):
    query = request.GET.get('q', '')
    data = [
        {
            'id': work.id,
            'synopsis': work.synopsis[:50] + '…',
            'title': work.title,
            'year': '' if not work.date else work.date.year,
        } for work in Work.objects.filter(category__slug=category, title__icontains=query).popular()[:10]
    ]
    return HttpResponse(json.dumps(data), content_type='application/json')

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
