from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import FormMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.timezone import utc

from django.dispatch import receiver
from django.db.models import Count
from django.db import connection
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added
from mangaki.models import Work, Anime, Manga, Rating, Page, Profile, Artist, Suggestion, SearchIssue, Announcement, Recommendation
from mangaki.mixins import AjaxableResponseMixin
from mangaki.forms import SuggestionForm
from mangaki.utils.mal import lookup_mal_api, import_mal, retrieve_anime
from mangaki.utils.recommendations import get_recommendations

from markdown import markdown
from urllib.parse import urlencode
from itertools import groupby
from random import shuffle
import datetime
import json


POSTERS_PER_PAGE = 24
TITLES_PER_PAGE = 24
USERNAMES_PER_PAGE = 24

def display_queries():
    for line in connection.queries:
        print(line['sql'][:100], line['time'])


def get_rated_works(user):
    rated_works = {}
    for rating in Rating.objects.filter(user=user):
        rated_works[rating.work_id] = rating.choice
    return rated_works


def update_poster_if_nsfw(obj, user):
    if obj.nsfw and (not user.is_authenticated() or not user.profile.nsfw_ok):
        obj.poster = '/static/img/nsfw.jpg'  # NSFW


class AnimeDetail(AjaxableResponseMixin, FormMixin, DetailView):
    model = Anime
    form_class = SuggestionForm

    def get_success_url(self):
        return 'anime/%d' % self.object.pk

    def get_context_data(self, **kwargs):
        context = super(AnimeDetail, self).get_context_data(**kwargs)
        update_poster_if_nsfw(self.object, self.request.user)
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
        update_poster_if_nsfw(self.object, self.request.user)
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
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.save()
        return super(MangaDetail, self).form_valid(form)


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
            score[work_id] = nb_likes if nb_dislikes <= 5 and nb_likes >= 3 else 0
    return score


def get_bundle(category, sort_mode, my_rated_works={}):
    already_rated = ', '.join(map(str, my_rated_works.keys())) if my_rated_works.keys() else '0'
    work_query = 'SELECT mangaki_{category}.work_ptr_id, mangaki_work.id, mangaki_work.title, mangaki_work.poster, mangaki_work.nsfw, COUNT(mangaki_work.id) rating_count FROM mangaki_{category}, mangaki_work, mangaki_rating WHERE mangaki_{category}.work_ptr_id = mangaki_work.id AND mangaki_rating.work_id = mangaki_work.id AND (mangaki_{category}.work_ptr_id NOT IN (' + already_rated + ')) GROUP BY mangaki_work.id, mangaki_{category}.work_ptr_id HAVING COUNT(mangaki_work.id) >= {min_ratings} ORDER BY {order_by}'
    if category == 'anime':
        obj = Anime.objects
    elif category == 'manga':
        obj = Manga.objects
    if sort_mode == 'popularity':
        return obj.raw(work_query.format(category=category, min_ratings=6 if category == 'anime' else 0, order_by='rating_count DESC'))
    elif sort_mode == 'top':
        return obj.raw(work_query.format(category=category, min_ratings=100 if category == 'anime' else 1, order_by='rating_count DESC'))
    elif sort_mode == 'controversy' or sort_mode == 'random':
        return obj.raw(work_query.format(category=category, min_ratings=6 if category == 'anime' else 1, order_by='rating_count DESC'))
    else:
        return obj.raw(work_query.format(category=category, min_ratings=1 if category == 'anime' else 0, order_by='title'))


def pick_card(bundle, sort_mode, my_rated_works, deja_vu):
    score = get_scores(bundle, sort_mode)
    score_max = float('-inf')
    card = None
    for work in bundle:
        if work.id not in my_rated_works and str(work.id) not in deja_vu and score.get(work.id, 0) > score_max:
            card = work
            score_max = score.get(work.id, 0)
    return card


def get_card(request, category, sort_id=1):
    deja_vu = request.GET.get('dejavu', '').split(',')
    sort_mode = ['popularity', 'controversy', 'top', 'random'][int(sort_id) - 1]
    my_rated_works = get_rated_works(request.user) if request.user.is_authenticated() else {}
    bundle = list(get_bundle(category, sort_mode, my_rated_works))
    work = pick_card(bundle, sort_mode, my_rated_works, deja_vu)
    update_poster_if_nsfw(work, request.user)
    card = {'id': work.id, 'title': work.title, 'poster': work.poster, 'category': category, 'synopsis': work.synopsis}
    return HttpResponse(json.dumps(card), content_type='application/json')


class AnimeList(ListView):
    model = Anime
    context_object_name = 'anime'

    def get_queryset(self):
        sort_mode = self.request.GET.get('sort', 'mosaic')
        if sort_mode == 'mosaic':
            return Anime.objects.none()
        letter = self.request.GET.get('letter', '')
        bundle = get_bundle('anime', sort_mode)
        if letter:
            bundle = Anime.objects.all()
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
        context = super(AnimeList, self).get_context_data(**kwargs)
        context['object_list'] = list(context['object_list'])
        if sort_mode == 'mosaic':
            context['object_list'] = [Work(title='Chargement…', poster='/static/img/chiro.gif') for _ in range(4)]
        elif sort_mode == 'random':
            score = get_scores(context['object_list'], sort_mode)
            context['object_list'] = list(filter(lambda anime: score[anime.id], context['object_list']))
            shuffle(context['object_list'])
        elif sort_mode == 'top' or sort_mode == 'controversy':
            score = get_scores(context['object_list'], sort_mode)
            context['object_list'].sort(key=lambda anime: -score[anime.id])
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
            update_poster_if_nsfw(obj, self.request.user)
            if self.request.user.is_authenticated():
                obj.rating = my_rated_works.get(obj.id, None)  # Necessary for displaying current ratings on AnimeList
        context['object_list'] = anime_list
        return context


class MangaList(ListView):
    model = Manga
    context_object_name = 'manga'

    def get_queryset(self):
        sort_mode = self.request.GET.get('sort', 'mosaic')
        if sort_mode == 'mosaic':
            return Manga.objects.none()
        letter = self.request.GET.get('letter', '')
        bundle = get_bundle('manga', sort_mode)
        if letter:
            bundle = Manga.objects.all()
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
        context['object_list'] = list(context['object_list'])
        if sort_mode == 'mosaic':
            context['object_list'] = [Work(title='Chargement…', poster='/static/img/chiro.gif') for _ in range(4)]
        elif sort_mode == 'random':
            shuffle(context['object_list'])
        elif sort_mode == 'top' or sort_mode == 'controversy':
            score = get_scores(context['object_list'], sort_mode)
            context['object_list'].sort(key=lambda anime: -score[anime.id])
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
            update_poster_if_nsfw(obj, self.request.user)
            if self.request.user.is_authenticated():
                obj.rating = my_rated_works.get(obj.id, None)
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
    try:
        is_shared = Profile.objects.get(user__username=username).is_shared
    except Profile.DoesNotExist:
        Profile(user=request.user).save()  # À supprimer à terme # Tu parles, maintenant ça va être encore plus compliqué
        is_shared = True
    user = User.objects.get(username=username)
    category = request.GET.get('category', 'anime')
    ordering = ['favorite', 'willsee', 'like', 'neutral', 'dislike', 'wontsee']
    rating_list = sorted(Rating.objects.filter(user__username=username).select_related('work', 'work__anime', 'work__manga'), key=lambda x: (ordering.index(x.choice), x.work.title))
    seen_anime_list = []
    unseen_anime_list = []
    seen_manga_list = []
    unseen_manga_list = []

    received_recommendation_list = []
    sent_recommendation_list = []
    received_recommendations = Recommendation.objects.filter(target_user__username=username)
    sent_recommendations = Recommendation.objects.filter(user__username=username)
    for reco in received_recommendations:
        try:
            reco.work.anime
            received_recommendation_list.append({'category': 'anime', 'id': reco.work.id, 'title': reco.work.title, 'username': reco.user.username})
        except Anime.DoesNotExist:
            received_recommendation_list.append({'category': 'manga', 'id': reco.work.id, 'title': reco.work.title, 'username': reco.user.username})
    for reco in sent_recommendations:
        try:
            reco.work.anime
            sent_recommendation_list.append({'category': 'anime', 'id': reco.work.id, 'title': reco.work.title, 'username': reco.target_user.username})
        except Anime.DoesNotExist:
            sent_recommendation_list.append({'category': 'manga', 'id': reco.work.id, 'title': reco.work.title, 'username': reco.target_user.username})

    for rating in rating_list:
        seen = rating.choice in ['favorite', 'like', 'neutral', 'dislike']
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
    member_time = datetime.datetime.now().replace(tzinfo=utc) - user.date_joined
    seen_list = seen_anime_list if category == 'anime' else seen_manga_list
    unseen_list = unseen_anime_list if category == 'anime' else unseen_manga_list
    return render(request, 'profile.html', {
        'username': username,
        'is_shared': is_shared,
        'category': category,
        'avatar_url': user.profile.get_avatar_url(),
        'member_days': member_time.days,
        'anime_count': len(seen_anime_list),
        'manga_count': len(seen_manga_list),
        'seen_list': seen_list if is_shared else [],
        'unseen_list': unseen_list if is_shared else [],
        'received_recommendation_list': received_recommendation_list if is_shared else [],
        'sent_recommendation_list': sent_recommendation_list if is_shared else [],
    })


def index(request):
    if request.user.is_authenticated():
        if Rating.objects.filter(user=request.user).count() == 0:
            return redirect('/anime/')
    # texte = Announcement.objects.get(title='Flash News').text
    # context = {'annonce': texte}
    return render(request, 'index.html')

 
def about(request):
    return render(request, 'about.html')


def events(request):
    return render(request, 'events.html')


def rate_work(request, work_id):
    if request.user.is_authenticated() and request.method == 'POST':
        work = get_object_or_404(Work, id=work_id)
        choice = request.POST.get('choice', '')
        if choice not in ['like', 'neutral', 'dislike', 'willsee', 'wontsee', 'favorite']:
            return HttpResponse()        
        if Rating.objects.filter(user=request.user, work=work, choice=choice).count() > 0:
            Rating.objects.filter(user=request.user, work=work, choice=choice).delete()
            return HttpResponse('none')
        Rating.objects.update_or_create(user=request.user, work=work, defaults={'choice': choice})
        return HttpResponse(choice)
    return HttpResponse()


def recommend_work(request, work_id,target_id):
    if request.user.is_authenticated() and request.method == 'POST':
        work = get_object_or_404(Work, id=work_id)
        target_user = get_object_or_404(User, id=target_id)
        if not Rating.objects.filter(user=target_user, work=work, choice__in=['favorite','like','neutral','dislike']):
            Recommendation.objects.update_or_create(user=request.user, work=work, target_user=target_user)
    return HttpResponse()


def get_users(request, query=''):
    data = []
    for user in User.objects.all() if not query else User.objects.filter(username__icontains=query):
        data.append({'id': user.id, 'username': user.username, 'tokens': user.username.lower().split()})
    return HttpResponse(json.dumps(data), content_type='application/json')

def get_user_for_recommendations(request, work_id, query=''):
    data = []
    for user in User.objects.all() if not query else User.objects.filter(username__icontains=query):
        data.append({'id': user.id, 'username': user.username, 'work_id' : work_id, 'tokens': user.username.lower().split()})
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
    # category = request.GET.get('category', 'all')
    #editor = request.GET.get('editor', '')
    reco_list = []
    my_rated_works = {}
    willsee = set()
    if request.user.is_authenticated():
        if request.user.profile.reco_willsee_ok:
            for rating in Rating.objects.filter(user=request.user):
                if rating.choice != 'willsee':
                    my_rated_works[rating.work_id] = rating.choice
                else:
                    willsee.add(rating.work.id)
        else:
            for rating in Rating.objects.filter(user=request.user):
                my_rated_works[rating.work_id] = rating.choice
    for work, is_manga in get_recommendations(request.user, my_rated_works, category, editor):
        update_poster_if_nsfw(work, request.user)
        reco_list.append({'id': work.id, 'title': work.title, 'poster': work.poster, 'category': 'manga' if is_manga else 'anime', 'rating': 'willsee' if work.id in willsee else 'None'})  # Does not work
    return HttpResponse(json.dumps(reco_list), content_type='application/json')

def remove_reco(request, work_id, username, targetname):
    work = get_object_or_404(Work, id=work_id)
    user = get_object_or_404(User, username=username)
    target = get_object_or_404(User, username=targetname)
    Recommendation.objects.get(work=work,user=user,target_user=target).delete()


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

@receiver(user_signed_up)
@receiver(social_account_added)
def register_profile(sender, **kwargs):
    user = kwargs['user']
    Profile(user=user).save()
