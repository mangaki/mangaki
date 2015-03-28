from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import FormMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.dispatch import receiver
from django.db.models import Count
from django.db import connection
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added
from mangaki.models import Work, Anime, Manga, Rating, Page, Profile, Artist, Suggestion, Neighborship
from mangaki.mixins import AjaxableResponseMixin
from mangaki.forms import SuggestionForm
from mangaki.api import get_discourse_data
from collections import Counter
from markdown import markdown
from secret import MAL_USER, MAL_PASS
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
import datetime
import requests
import json
import html
import re

POSTERS_PER_PAGE = 24
TITLES_PER_PAGE = 24

def display_queries():
    for line in connection.queries:
        print(line['sql'])

def get_rated_works(user):
    rated_works = {}
    for rating in Rating.objects.filter(user=user).select_related('work'):
        rated_works[rating.work.id] = rating.choice
    return rated_works

class AnimeDetail(AjaxableResponseMixin, FormMixin, DetailView):
    model = Anime
    form_class = SuggestionForm

    def get_success_url(self):
        return 'anime/%d' % self.object.pk

    def get_context_data(self, **kwargs):
        context = super(AnimeDetail, self).get_context_data(**kwargs)
        if self.object.nsfw:
            context['object'].poster = '/static/img/nsfw.jpg'  # NSFW
        context['object'].source = context['object'].source.split(',')[0]
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
        else:
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
        if self.object.nsfw:
            context['object'].poster = '/static/img/nsfw.jpg'  # NSFW
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
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.save()
        return super(MangaDetail, self).form_valid(form)


class AnimeList(ListView):
    model = Anime
    context_object_name = 'anime'

    def get_queryset(self):
        sort_mode = self.request.GET.get('sort')
        letter = self.request.GET.get('letter')
        bundle = Anime.objects.annotate(Count('rating')).filter(rating__count__gte=1).order_by('id')  # Rated by at least one person
        if letter:
            sort_mode = 'alpha'
            if letter == '0':  # '#'
                bundle = bundle.exclude(title__regex=r'^[a-zA-Z]')
            else:
                bundle = bundle.filter(title__istartswith=letter)
        if sort_mode == 'alpha':
            bundle = bundle.order_by('title')
        return bundle

    def get_context_data(self, **kwargs):
        my_rated_works = get_rated_works(self.request.user)
        sort_mode = self.request.GET.get('sort', 'popularity')
        flat_mode = self.request.GET.get('flat', '0')
        letter = self.request.GET.get('letter', '')
        page = int(self.request.GET.get('page', '1'))
        context = super(AnimeList, self).get_context_data(**kwargs)
        paginator = Paginator(context['object_list'], TITLES_PER_PAGE if flat_mode == '1' else POSTERS_PER_PAGE)

        try:
            anime_list = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            anime_list = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            anime_list = paginator.page(paginator.num_pages)

        context['params'] = {'sort': sort_mode, 'letter': letter, 'page': page, 'flat': flat_mode}
        context['url'] = urlencode({'sort': sort_mode, 'letter': letter})
        context['anime_count'] = Anime.objects.count()
        context['pages'] = filter(lambda x: 1 <= x <= paginator.num_pages, range(anime_list.number - 2, anime_list.number + 2 + 1))
        context['template_mode'] = 'work_no_poster.html' if flat_mode == '1' else 'work_poster.html'
        for obj in anime_list:
            if obj.nsfw:
                obj.poster = '/static/img/nsfw.jpg'  # NSFW
            if self.request.user.is_authenticated():
                obj.rating = my_rated_works.get(obj.id, None)
        context['object_list'] = anime_list
        return context


class MangaList(ListView):
    model = Manga
    context_object_name = 'manga'

    def get_queryset(self):
        sort_mode = self.request.GET.get('sort')
        letter = self.request.GET.get('letter')
        bundle = Manga.objects.annotate(Count('rating')).filter(rating__count__gte=0).order_by('id')  # Rated by at least zero person (to be modified)
        if letter:
            sort_mode = 'alpha'
            if letter == '0':  # '#'
                bundle = bundle.exclude(title__regex=r'^[a-zA-Z]')
            else:
                bundle = bundle.filter(title__istartswith=letter)
        if sort_mode == 'alpha':
            bundle = bundle.order_by('title')
        return bundle

    def get_context_data(self, **kwargs):
        my_rated_works = get_rated_works(self.request.user)
        sort_mode = self.request.GET.get('sort', 'popularity')
        flat_mode = self.request.GET.get('flat', '0')
        letter = self.request.GET.get('letter', '')
        page = int(self.request.GET.get('page', '1'))
        context = super(MangaList, self).get_context_data(**kwargs)
        paginator = Paginator(context['object_list'], TITLES_PER_PAGE if flat_mode == '1' else POSTERS_PER_PAGE)

        try:
            manga_list = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            manga_list = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            manga_list = paginator.page(paginator.num_pages)

        context['params'] = {'sort': sort_mode, 'letter': letter, 'page': page, 'flat': flat_mode}
        context['url'] = urlencode({'sort': sort_mode, 'letter': letter})
        context['manga_count'] = Manga.objects.count()
        context['pages'] = filter(lambda x: 1 <= x <= paginator.num_pages, range(manga_list.number - 2, manga_list.number + 2 + 1))
        context['template_mode'] = 'work_no_poster.html' if flat_mode == '1' else 'work_poster.html'

        for obj in manga_list:
            if obj.nsfw:
                obj.poster = '/static/img/nsfw.jpg'  # NSFW
            if self.request.user.is_authenticated():
                obj.rating = my_rated_works.get(obj.id, None)
        context['object_list'] = manga_list
        return context


class UserList(ListView):
    model = User
    # context_object_name = 'anime'

    def get_queryset(self):
        return User.objects.filter(profile__is_shared=True).order_by('-id')[:5]

    def get_context_data(self, **kwargs):
        context = super(UserList, self).get_context_data(**kwargs)
        context['trio_elm'] = User.objects.filter(username__in=['jj', 'Lily', 'Sedeto'])
        return context


def get_profile(request, username):
    try:
        is_shared = Profile.objects.get(user__username=username).is_shared
    except Profile.DoesNotExist:
        Profile(user=request.user).save()  # À supprimer à terme
        is_shared = True
    ordering = ['willsee', 'like', 'neutral', 'dislike', 'wontsee']
    rating_list = sorted(Rating.objects.filter(user__username=username).select_related('work', 'work__anime', 'work__manga'), key=lambda x: (ordering.index(x.choice), x.work.title))
    seen_anime_list = []
    unseen_anime_list = []
    seen_manga_list = []
    unseen_manga_list = []
    for rating in rating_list:
        seen = rating.choice in ['like', 'neutral', 'dislike']
        try:
            rating.work.anime
            if seen:
                seen_anime_list.append(rating)
            else:
                unseen_anime_list.append(rating)
        except Anime.DoesNotExist:
            if seen:
                seen_manga_list.append(rating)
            else:
                unseen_manga_list.append(rating)
    discourse_data = get_discourse_data(User.objects.get(username=username).email)
    member_time = datetime.datetime.now() - datetime.datetime.strptime(discourse_data['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
    return render(request, 'profile.html', {
        'username': username,
        'is_shared': is_shared,
        'avatar_url': discourse_data['avatar'].format(size=150),
        'member_days': member_time.days,
        'anime_count': len(seen_anime_list),
        'manga_count': len(seen_manga_list),
        'seen_anime_list': seen_anime_list if is_shared else [],
        'unseen_anime_list': unseen_anime_list if is_shared else [],
        'seen_manga_list': seen_manga_list if is_shared else [],
        'unseen_manga_list': unseen_manga_list if is_shared else []
    })


def index(request):
    if request.user.is_authenticated():
        if Rating.objects.filter(user=request.user).count() == 0:
            return redirect('/anime/')
        else:
            return redirect('/u/%s' % request.user.username)
    return render(request, 'index.html')


def rate_work(request, work_id):
    if request.user.is_authenticated() and request.method == 'POST':
        print(work_id)
        work = get_object_or_404(Work, id=work_id)
        print(work.title)
        choice = request.POST.get('choice', '')
        if choice not in ['like', 'neutral', 'dislike', 'willsee', 'wontsee']:
            return HttpResponse()
        if Rating.objects.filter(user=request.user, work=work, choice=choice).count() > 0:
            Rating.objects.filter(user=request.user, work=work, choice=choice).delete()
            return HttpResponse('none')
        Rating.objects.update_or_create(user=request.user, work=work, defaults={'choice': choice})
        return HttpResponse(choice)
    return HttpResponse()


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
    return HttpResponse()


def get_extra_works(request, query, redirect=True):
    entries = lookup_mal_api(query)
    unknown = Artist.objects.get(id=1)
    for entry in entries:
        if Anime.objects.filter(poster=entry['image']).count() == 0:  # SCANDALE
            title = entry['english'] if entry['english'] else entry['title']
            if '0000' in entry['start_date']:
                anime_date = None
            elif '00-00' in entry['start_date']:
                anime_date = entry['start_date'].replace('00-00', '01-01')
            elif '-00' in entry['start_date']:
                anime_date = entry['start_date'].replace('-00', '-01')
            else:
                anime_date = entry['start_date']

            Anime.objects.create(director=unknown, composer=unknown, title=title, source='http://myanimelist.net/anime/' + entry['id'], poster=entry['image'], date=anime_date)

    if redirect:
        return get_works(request, 'anime', query)

def get_recommendations(user, my_rated_works):
    values = {'like': 2, 'dislike': -2, 'neutral': 0.1, 'willsee': 0.5, 'wontsee': -0.5}
    works = Counter()
    nb_ratings = {}
    c = 0
    neighbors = Counter()
    for her in Rating.objects.filter(work__in=my_rated_works.keys()).select_related('work', 'user'):
        c += 1
        neighbors[her.user.id] += values[my_rated_works[her.work.id]] * values[her.choice]
    score_of_neighbor = {}
    for user_id, score in neighbors.most_common(10):
        score_of_neighbor[user_id] = score
    for her in Rating.objects.filter(user__id__in=score_of_neighbor.keys()).select_related('work', 'user'):
        if her.work.id not in works:
            works[her.work.id] = [values[her.choice], score]
            nb_ratings[her.work.id] = 1
        else:
            works[her.work.id][0] += values[her.choice]
            works[her.work.id][1] += score_of_neighbor[her.user.id]
            nb_ratings[her.work.id] += 1
    banned_works = set()
    for work_id in my_rated_works:
        if my_rated_works[work_id] != 'willsee':
            banned_works.add(work_id)
    for work_id in works:
        if nb_ratings[work_id] == 1 or work_id in banned_works:
            works[work_id] = (0, 0)
        else:
            works[work_id] = (float(works[work_id][0]) / nb_ratings[work_id], works[work_id][1])

    return works.most_common(4)


@login_required
def get_reco(request):
    reco_list = []
    my_rated_works = {}
    my_ratings = Rating.objects.filter(user=request.user).select_related('work')
    for rating in my_ratings:
        my_rated_works[rating.work.id] = rating.choice
    for work_id, _ in get_recommendations(request.user, my_rated_works):
        reco = Anime.objects.get(id=work_id)
        if work_id in my_rated_works:
            reco_list.append((reco, 'willsee'))
        else:
            reco_list.append((reco, ''))
    return render(request, 'mangaki/reco_list.html', {'reco_list': reco_list})


def update_shared(request):
    if request.user.is_authenticated() and request.method == 'POST':
        Profile.objects.filter(user=request.user).update(is_shared=request.POST['is_shared'] == 'true')
    return HttpResponse()


def lookup_mal_api(query):
    xml = re.sub(r'&([^alg])', r'&amp;\1', html.unescape(re.sub(r'&amp;([A-Za-z]+);', r'&\1;', requests.get('http://myanimelist.net/api/anime/search.xml', params={'q': query}, headers={'X-Real-IP': '251.223.201.179', 'User-Agent': 'Mozilla/5.0 (X11; Linux i686 on x86_64; rv:36.0) Gecko/20100101 Firefox/36.0'}, auth=(MAL_USER, MAL_PASS)).text).replace('&lt', '&lot;').replace('&gt;', '&got;')).replace('&lot;', '&lt').replace('&got;', '&gt;'))
    entries = []
    try:
        for entry in ET.fromstring(xml).findall('entry'):
            data = {}
            for child in entry:
                data[child.tag] = child.text
            entries.append(data)
    except ET.ParseError:
        pass
    return entries


def report_nsfw(request, pk):
    Anime.objects.filter(id=pk).update(nsfw=True)
    return redirect('/anime/%s' % pk)


@receiver(user_signed_up)
@receiver(social_account_added)
def register_profile(sender, **kwargs):
    user = kwargs['user']
    Profile(user=user).save()
