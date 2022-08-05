# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

import datetime
import json
from collections import Counter, OrderedDict
from itertools import zip_longest
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import urlencode

import allauth.account.views

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
# from django.contrib.postgres.search import SearchVector, SearchRank, SearchQuery
from django.contrib import messages
from django.core.exceptions import SuspiciousOperation, ObjectDoesNotExist
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import DatabaseError
from django.db.models import Case, IntegerField, When, Count
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone, translation
from django.utils.http import is_safe_url
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.defaults import server_error
from django.views.generic import View
from django.views.generic.detail import DetailView, SingleObjectMixin, SingleObjectTemplateResponseMixin
from django.views.generic.edit import FormMixin
from django.views.generic.list import ListView
from markdown import markdown
from natsort import natsorted

from mangaki.choices import (TOP_CATEGORY_CHOICES, WORK_CATEGORY_CHOICES,
                             SORT_MODE_CHOICES)
from mangaki.forms import SuggestionForm
from mangaki.mixins import AjaxableResponseMixin, JSONResponseMixin
from mangaki.models import (Artist, Category, FAQTheme, Page, Pairing, Profile, Ranking, Rating,
                            Recommendation, Staff, Suggestion, Evidence, Top, Trope, Work, WorkCluster)
from mangaki.utils.mal import client
from mangaki.tasks import import_mal, get_current_mal_import, redis_pool
from mangaki.utils.profile import (
    get_profile_ratings,
    build_profile_compare_function,
    get_profile_recommendations
)
from mangaki.utils.ratings import (clear_anonymous_ratings, current_user_rating, current_user_ratings,
                                   current_user_set_toggle_rating, get_anonymous_ratings)
from mangaki.utils.tokens import compute_token, NEWS_SALT
from mangaki.utils.recommendations import get_group_reco_algo
from irl.models import Partner


NB_POINTS_DPP = 10
RATINGS_PER_PAGE = 24
TITLES_PER_PAGE = 24
POSTERS_PER_PAGE = 24
ARTISTS_PER_PAGE = 24
USERNAMES_PER_PAGE = 24
FIXES_PER_PAGE = 5
NSFW_GRID_PER_PAGE = 5

REFERENCE_DOMAINS = (
    ('http://myanimelist.net', 'myAnimeList'),
    ('http://animeka.com', 'Animeka'),
    ('http://vgmdb.net', 'VGMdb'),
    ('http://anidb.net', 'AniDB'),
    ('https://anidb.net', 'AniDB'),
    ('https://anisearch.com', 'Anisearch'),
    ('https://notify.moe', 'Notify.moe'),
    ('https://anime-planet.com', 'Anime Planet'),
    ('https://anilist.co', 'AniList'),
    ('https://kitsu.io', 'Kitsu'),
    ('https://livechart.me', 'LiveChart.me')
)

RATING_COLORS = {
    'favorite': {'normal': '#f8d549', 'highlight': '#f8d549'},
    'like': {'normal': '#5cb85c', 'highlight': '#47a447'},
    'neutral': {'normal': '#f0ad4e', 'highlight': '#ec971f'},
    'dislike': {'normal': '#d9534f', 'highlight': '#c9302c'},
    'willsee': {'normal': '#337ab7', 'highlight': '#286090'},
    'wontsee': {'normal': '#5bc0de', 'highlight': '#31b0d5'}
}

VANILLA_UI_CONFIG_FOR_RATINGS = {
    'ui': [
        {
            'name': 'favorite',
            'title': _("Love")
        },
        {
            'name': "like",
            'title': _("Like")
        },
        {
            'name': "neutral",
            'title': _("Neutral")
        },
        {
            'name': "dislike",
            'title': _("Dislike")
        },
        {
            'name': 'willsee',
            'title': _("I want to see"),
            'extra_classes': ['rating_separator']
        },
        {
            'name': 'wontsee',
            'title': _("I don't want to see")
        }
    ],
    'endpoint': reverse_lazy('vote')
}

def deep_dict_merge(source: Dict, destination: Dict,
                    _path: Optional[List] = None) -> Dict:
    """
    **In-place** deep dict merge from source to destination.

    Will raise an exception if encounters distinct types for the same key.

    Args:
        source (dict)
        destination (dict)
        _path(str): internal implementation details to track recursive calls

    Returns: destination (dict).

    """
    if _path is None:
        _path = []

    for key in source.keys():
        if key in destination:
            if isinstance(source[key], dict) and isinstance(destination[key], dict):
                deep_dict_merge(source[key], destination[key],
                      _path + [key])
            elif source[key] == destination[key]:
                pass
            else:
                raise ValueError(
                    'Conflict at {}'.format(
                        '.'.join(_path + [key])
                    )
                )
        else:
            destination[key] = source[key]

    return destination

@method_decorator(ensure_csrf_cookie, name='dispatch')
class WorkDetail(AjaxableResponseMixin, FormMixin, SingleObjectTemplateResponseMixin, SingleObjectMixin, View):
    form_class = SuggestionForm
    queryset = Work.objects.select_related('category').prefetch_related('worktitle_set',
                                                                        'staff_set__role',
                                                                        'staff_set__artist')

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.category.slug != self.kwargs.get('category'):
            return HttpResponsePermanentRedirect(self.object.get_absolute_url())

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object.source = self.object.source.split(',')[0]

        context['config'] = VANILLA_UI_CONFIG_FOR_RATINGS

        context['genres'] = ', '.join(genre.title for genre in self.object.genre.all())

        if self.request.user.is_authenticated:
            context['suggestion_form'] = SuggestionForm(work=self.object, instance=Suggestion(user=self.request.user, work=self.object))
        context['rating'] = current_user_rating(self.request, self.object)

        context['references'] = {}
        for reference in self.object.reference_set.all():
            context['references'][reference.get_url()] = reference.source
        if 'AniDB' not in context['references'].values() and self.object.anidb_aid >= 1:
            url = f'https://anidb.net/anime/{self.object.anidb_aid}'
            context['references'][url] = 'AniDB'

        nb = Counter(Rating.objects.filter(work=self.object).values_list('choice', flat=True))
        labels = OrderedDict([
            ('favorite', 'Ajoutés aux favoris'),
            ('like', 'Ont aimé'),
            ('neutral', 'Neutre'),
            ('dislike', 'N\'ont pas aimé'),
            ('willsee', 'Ont envie de voir'),
            ('wontsee', 'N\'ont pas envie de voir'),
        ])
        seen_ratings = {'favorite', 'like', 'neutral', 'dislike'}
        total = sum(nb.values())
        if total > 0:
            context['stats'] = []
            seen_total = sum(nb[rating] for rating in seen_ratings)
            for rating, label in labels.items():
                if seen_total > 0 and rating not in seen_ratings:
                    continue
                context['stats'].append({'value': nb[rating], 'colors': RATING_COLORS[rating], 'label': label})
            context['seen_percent'] = round(100 * seen_total / float(total))

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.save()
        return super().form_valid(form)


class WorkListMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        work_list = list(context['object_list'])
        ratings = current_user_ratings(self.request, work_list)

        for work in work_list:
            work.rating = ratings.get(work.id, None)

        context['object_list'] = [
            {
                'work': work
            }
            for work in work_list
        ]
        return context


@method_decorator(ensure_csrf_cookie, name='dispatch')
class WorkList(WorkListMixin, ListView):
    paginate_by = POSTERS_PER_PAGE

    @cached_property
    def category(self):
        return get_object_or_404(Category, slug=self.kwargs.get('category'))

    @property
    def search_query(self):
        return self.request.GET.get('search', None)

    def flat(self):
        return self.request.GET.get('flat', 0)

    def watchlist_user(self):
        return self.request.GET.get('watchlist', None)

    def sort_mode(self):
        default = 'mosaic'
        sort = self.request.GET.get('sort', default)
        if self.search_query is not None and sort == default:
            return 'popularity'  # Mosaic cannot be searched through because it is random. We enforce the popularity as the second default when searching.
        else:
            return sort

    def get_queryset(self):
        search_text = self.search_query
        watchlist_user = self.watchlist_user()
        if watchlist_user is not None:
            work_ids = Rating.objects.filter(
                work__category=self.category, user__username=watchlist_user,
                choice='willsee').values_list('work_id', flat=True)
            self.queryset = Work.objects.filter(id__in=work_ids)
        else:
            self.queryset = self.category.work_set
        sort_mode = self.sort_mode()

        if sort_mode == 'new':
            self.queryset = self.queryset.filter(
                date__isnull=False, date__lt=datetime.date.today()).order_by('-date')
        elif sort_mode == 'upcoming':
            self.queryset = self.queryset.filter(
                date__isnull=False, date__gt=datetime.date.today()).order_by('date')            
        elif sort_mode == 'top':
            self.queryset = self.queryset.top()
        elif sort_mode == 'popularity':
            self.queryset = self.queryset.popular()
        elif sort_mode == 'controversy':
            self.queryset = self.queryset.controversial()
        elif sort_mode == 'alpha':
            letter = self.request.GET.get('letter', '0')
            if letter == '0':  # '#'
                self.queryset = self.queryset.exclude(title__regex=r'^[a-zA-Z]')
            else:
                self.queryset = self.queryset.filter(title__istartswith=letter)
            self.queryset = self.queryset.order_by('title')
        elif sort_mode == 'pearls':
            self.queryset = self.queryset.pearls()
        elif sort_mode == 'random':
            self.queryset = self.queryset.random().order_by('?')[:self.paginate_by]
        elif sort_mode == 'mosaic':
            self.queryset = self.queryset.none()
        else:
            raise Http404

        if search_text:
            # Another day we can attempt this more sophisticated use:
            # query = SearchQuery(search_text, search_type='phrase')
            # rank = SearchRank('titles_search', query)
            # https://medium.com/finimize-engineering/postgresql-performance-tuning-in-django-c8dd508d0ff6
            self.queryset = self.queryset.filter(titles_search=search_text)

        self.queryset = self.queryset.only('id', 'title', 'int_poster', 'ext_poster', 'nsfw', 'synopsis', 'category__slug')

        return self.queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slot_sort_types = ['popularity', 'controversy', 'top', 'random']
        search_text = self.search_query
        sort_mode = self.sort_mode()
        flat = self.flat()

        context['search'] = search_text
        context['flat'] = flat
        context['sort_mode'] = sort_mode
        context['sort_mode_display'] = dict(SORT_MODE_CHOICES)[sort_mode]
        context['sort_modes'] = SORT_MODE_CHOICES
        context['letter'] = self.request.GET.get('letter', '')
        context['category'] = self.category.slug
        context['config'] = VANILLA_UI_CONFIG_FOR_RATINGS
        context['enable_kb_shortcuts'] = (False if self.request.user.is_anonymous
        else self.request.user.profile.keyboard_shortcuts_enabled)

        if sort_mode == 'mosaic':
            context['object_list'] = [
                {
                    'slot_type': slot_sort_type,
                    'work': Work(title='Chargement…', ext_poster='/static/img/chiro.gif')
                }
                for slot_sort_type in slot_sort_types
            ]

        return context

    def render_to_response(self, context):
        if context.get('paginator') and context['paginator'].count == 1:  # Redirect to work detail if only result
            unique_work = self.queryset.first()
            return redirect('work-detail', category=self.category.slug, pk=unique_work.pk)
        else:
            return super(WorkList, self).render_to_response(context)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class ArtistList(ListView):
    paginate_by = ARTISTS_PER_PAGE

    def get_queryset(self):
        queryset = Artist.objects.all()
        if self.search_query:
            return queryset.filter(name__icontains=self.search_query)
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nb_artists'] = Artist.objects.count()
        context['search'] = self.search_query
        return context

    @property
    def search_query(self):
        return self.request.GET.get('search', None)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class ArtistDetail(SingleObjectMixin, WorkListMixin, ListView):
    template_name = 'mangaki/artist_detail.html'
    paginate_by = POSTERS_PER_PAGE

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=Artist.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Work.objects.filter(id__in=Staff.objects.filter(artist=self.object).values('work_id')).order_by('title')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['artist'] = self.object
        context['config'] = VANILLA_UI_CONFIG_FOR_RATINGS

        return context


def get_profile(request,
                username: str = None):
    is_anonymous = False
    if username:
        user = get_object_or_404(User.objects.select_related('profile'), username=username)
    else:
        user = request.user
        is_anonymous = not request.user.is_authenticated

    if is_anonymous or username is None:
        is_shared = True
    elif user == request.user:
        is_shared = True
    else:
        is_shared = user.profile.is_shared

    can_see = is_shared or user == request.user
    algo_name = request.GET.get('algo', None)

    member_time = (datetime.date.today() - user.date_joined.date()
                   if (can_see and not is_anonymous) else None)

    is_me = request.user == user
    if request.user.is_authenticated:
        is_friend = not is_me \
            and request.user.profile.friends.filter(pk=user.pk).exists()
    else:
        is_friend = False
    context = {
        'meta': {
            'debug_vue': settings.DEBUG_VUE_JS,
            'mal': {
                'is_available': client.is_available and (redis_pool is not None),
                'pending_import': None if (not is_me) or is_anonymous else get_current_mal_import(request.user),
            },
            'config': VANILLA_UI_CONFIG_FOR_RATINGS,
            'can_see': can_see,
            'username': request.user.username,
            'is_shared': is_shared,
            'is_me': is_me,
            'is_anonymous': is_anonymous,
            'ratings_disabled': request.user != user and not is_anonymous,
            'algo_name': algo_name
        },
        'profile': {
            'avatar_url': user.profile.avatar_url if (not is_anonymous and can_see) else None,
            'member_days': member_time.days if member_time else None,
            'username': user.username,
            'is_friend': is_friend
        },
    }

    return user, context


def get_profile_preferences(request,
                            username: str = None):
    if username is None and request.user.is_authenticated:
        return redirect('profile-preferences', request.user.username, permanent=True)

    user, ctx = get_profile(request, username)

    if ctx['meta']['is_anonymous']:
        return redirect('profile')

    new_ctx = {
        'meta': {
           'section': 'preferences'
        }
    }

    return render(request, 'profile_preferences.html',
                  deep_dict_merge(ctx, new_ctx))


def get_profile_friendlist(request):
    if not request.user.is_authenticated:
        return redirect('account_login')

    user, ctx = get_profile(request, request.user.username)

    friendlists = {
        'mutual': {
            'name': _('My friends'),
            'friends': []
        },
        'pending': {
            'name': _('My pending friend requests'),
            'friends': []
        }
    }
    for friend in request.user.profile.friends.all():
        friend_data = {
            'username': friend.username,
            'is_shared': friend.profile.is_shared
        }
        if friend.profile.is_shared \
                or friend.profile.friends.filter(pk=request.user.pk).exists():
            friendlists['mutual']['friends'].append(friend_data)
        else:
            friendlists['pending']['friends'].append(friend_data)

    new_ctx = {
        'meta': {
           'section': 'friendlist'
        },
        'friendlists': friendlists
    }

    return render(request, 'profile_friendlist.html',
                  deep_dict_merge(ctx, new_ctx))


def get_profile_works(request,
                      username: str = None,
                      category: str = None,
                      status: str = None):
    if username is None and request.user.is_authenticated:
        return redirect('profile-works', request.user.username, category or 'anime', status or 'seen', permanent=True)

    user, ctx = get_profile(request, username)

    if category is None or status is None:
        if user.username:
            return redirect('profile-works', user.username, category or 'anime', status or 'seen', permanent=True)
        else:
            return redirect('my-profile', category or 'anime', status or 'seen', permanent=True)

    seen_works = status == "seen"
    algo_name = request.GET.get('algo', None)
    flat = request.GET.get('flat', None)
    # FIXME: We should move natural sorting on the database-side.
    # This way, we can keep a queryset until the end.
    # Eventually, we pass it as-is to the paginator, so we have better performance and less memory consumption.
    # Currently, we load the *entire set* of ratings for a (seen/willsee|wontsee) category of works.
    ratings, counts = get_profile_ratings(request,
                                          category,
                                          seen_works,
                                          ctx['meta']['can_see'],
                                          ctx['meta']['is_anonymous'],
                                          user)

    compare_function = build_profile_compare_function(algo_name,
                                                      ratings,
                                                      user)
    rating_list = natsorted(ratings, key=compare_function)

    work_rating_list = []
    for rating in rating_list:
        work = rating.work
        work.rating = rating.choice
        work_rating_list.append({'work': work})

    if category == 'recommendation':
        received_recommendation_list, sent_recommendation_list = get_profile_recommendations(
            ctx['meta']['is_anonymous'],
            ctx['meta']['can_see'],
            user
        )
    else:
        received_recommendation_list = sent_recommendation_list = []

    if ctx['meta']['can_see'] and not ctx['meta']['is_anonymous'] and not received_recommendation_list:
        reco_count = Recommendation.objects.filter(target_user=user).count()
    else:
        reco_count = len(received_recommendation_list)

    paginator = Paginator(work_rating_list, RATINGS_PER_PAGE)
    page = request.GET.get('page')

    try:
        paginated_work_rating_list = paginator.page(page)
    except PageNotAnInteger:
        paginated_work_rating_list = paginator.page(1)
    except EmptyPage:
        paginated_work_rating_list = paginator.page(paginator.num_pages)

    new_ctx = {
        'meta': {
            'category': category,
            'seen': seen_works,
            'algo_name': algo_name,
            'section': 'works',
            'status': status,
            'flat': flat
        },
        'profile': {
            'seen_anime_count': counts['seen_anime'],
            'seen_manga_count': counts['seen_manga'],
            'unseen_anime_count': counts['unseen_anime'],
            'unseen_manga_count': counts['unseen_manga'],
            'reco_count': reco_count,
            'username': user.username
        },
        'work_rating_list': paginated_work_rating_list,
        'recommendations': {
            'received': received_recommendation_list,
            'sent': sent_recommendation_list
        },
    }
    return render(request, 'profile_works.html',
                  deep_dict_merge(ctx, new_ctx))


def index(request):
    if request.user.is_authenticated:
        if Rating.objects.filter(user=request.user).count() == 0:
            return redirect('/anime/')
    # texte = Announcement.objects.get(title='Flash News').text
    # context = {'annonce': texte}
    partners = Partner.objects.filter()
    return render(request, 'index.html', {
        'partners': partners,
        'is_mal_import_available': client.is_available
    })


def about(request, lang):
    if lang != '':
        translation.activate(lang)
        request.session[translation.LANGUAGE_SESSION_KEY] = lang
    return render(request, 'about.html')


def top(request, category_slug):
    categories = dict(TOP_CATEGORY_CHOICES)
    if category_slug not in categories:
        raise Http404
    try:
        top = Top.objects.filter(category=category_slug).latest('date')
    except Top.DoesNotExist:
        raise Http404
    data = []
    rankings = Ranking.objects.filter(top=top).prefetch_related('content_object').order_by('-score')
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
    if request.method == 'POST':
        work = get_object_or_404(Work, id=work_id)
        choice = request.POST.get('choice', '')
        if choice not in ['like', 'neutral', 'dislike', 'willsee', 'wontsee', 'favorite']:
            return HttpResponse()
        choice = current_user_set_toggle_rating(request, work, choice)
        if choice is None:
            return HttpResponse('none')
        else:
            return HttpResponse(choice)

    else:
        return HttpResponse()


def add_friend(request, username: str = None):
    if request.user.is_authenticated and request.method == 'POST':
        target_user = get_object_or_404(User.objects.select_related('profile'),
                                        username=username)
        if target_user == request.user:
            return HttpResponse()
        request.user.profile.friends.add(target_user)
    return HttpResponse()


def del_friend(request, username: str = None):
    if request.user.is_authenticated and request.method == 'POST':
        target_user = get_object_or_404(User.objects.select_related('profile'),
                                        username=username)
        if target_user == request.user:
            return HttpResponse()
        request.user.profile.friends.remove(target_user)
    return HttpResponse()


def toggle_friend(request, username: str = None):
    if request.user.is_authenticated and request.method == 'POST':
        target_user = get_object_or_404(User.objects.select_related('profile'),
                                        username=username)
        group = set(request.session.setdefault(
            settings.RECO_GROUP_SESSION_KEY, [request.user.username]))
        if target_user.username in group:
            group.remove(target_user.username)
        # should you be able to recommend with someone with public profile but
        # who you have not friended yet?
        elif request.user.profile.friends.filter(pk=target_user.pk).exists() \
                and (target_user.profile.is_shared
                     or target_user.profile.friends
                         .filter(pk=request.user.pk).exists()):
            group.add(target_user.username)
        group.add(request.user.username)
        request.session[settings.RECO_GROUP_SESSION_KEY] = list(group)
        return HttpResponse(json.dumps(list(group)))
    return HttpResponse()


def recommend_work(request, work_id, target_id):
    if request.user.is_authenticated and request.method == 'POST':
        work = get_object_or_404(Work, id=work_id)
        target_user = get_object_or_404(User, id=target_id)
        if target_user == request.user:
            return HttpResponse('nonsense')
        if Recommendation.objects.filter(user=request.user, work=work, target_user=target_user).count() > 0:
            return HttpResponse('double')
        if not Rating.objects.filter(user=target_user, work=work,
                                     choice__in=['favorite', 'like', 'neutral', 'dislike']):
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
        data.append(
            {'id': user.id, 'username': user.username, 'work_id': work_id, 'tokens': user.username.lower().split()})
    return HttpResponse(json.dumps(data), content_type='application/json')


def get_friends(request):
    query = request.GET.get('q', '')
    data = []

    if request.user.is_authenticated:
        oriented_friends = request.user.profile.friends
        friends = oriented_friends.all() if not query \
            else oriented_friends.filter(username__icontains=query)
        # TODO: only n=10? first results
        for user in friends.order_by('username')[:10]:
            # TODO: Improve this to use only one request if possible
            if user.profile.is_shared \
                    or user.profile.friends.filter(pk=request.user.pk) \
                                           .exists():
                data.append({'username': user.username,
                             'type': 'group', # hack for autocomplete.js to know purpose, to clean later
                             'tokens': user.username.lower().split()})
    return HttpResponse(json.dumps(data), content_type='application/json')


class MarkdownView(DetailView):
    model = Page
    slug_field = 'name'
    template_name = 'static.html'

    def get_context_data(self, **kwargs):
        return {'html': markdown(self.object.markdown)}


def get_works(request, category):
    query = request.GET.get('q', '')
    data = [
        {
            'id': work.id,
            'synopsis': work.synopsis[:50] + '…',
            'title': work.title,
            'year': '' if not work.date else work.date.year,
        } for work in Work.objects.filter(category__slug=category).search(query).popular()[:10]
    ]
    return HttpResponse(json.dumps(data), content_type='application/json')


def get_reco_algo_list(request, algo_name, category, merge_type=None):
    reco_list = []
    NB_RECO = 8
    if request.user.is_authenticated:
        group_reco = request.session.setdefault(
            settings.RECO_GROUP_SESSION_KEY, [request.user.username]
        )
        if len(group_reco) > 1:
            # its likely the rows will be 3 large, so 9 works better than 8
            NB_RECO = 9
        friend_ids = list(
            user_id[0] for user_id in
            request.user.profile.friends.filter(username__in=group_reco)
                                        .values_list('id')
        )
        data = get_group_reco_algo(request, friend_ids, algo_name, category,
                                   merge_type)
    else:
        data = get_group_reco_algo(request, None, algo_name, category)
    works = data['works']
    categories = dict(WORK_CATEGORY_CHOICES)
    ratings_bulk = Rating.objects.filter(user__pk=request.user.pk) \
                                 .filter(work__id__in=[
                                     works[work_id].id
                                     for work_id in data['work_ids'][:NB_RECO]
                                 ])
    ratings = dict()
    for rating in ratings_bulk:
        ratings[rating.work.id] = rating.choice
    for work_id in data['work_ids'][:NB_RECO]:
        work = works[work_id]
        reco_list.append({'id': work.id, 'title': work.title,
                          'poster': work.ext_poster, 'synopsis': work.synopsis,
                          'category_slug': work.category.slug,
                          'category': str(categories[work.category.slug]),
                          'rating': ratings.get(work.id, None)})
    return HttpResponse(json.dumps(reco_list), content_type='application/json')


def remove_all_anon_ratings(request):
    if request.method == 'POST':
        clear_anonymous_ratings(request.session)
        return redirect('home')
    else:
        raise Http404


def remove_reco(request, work_id, username, targetname):
    if request.method == 'POST':
        work = get_object_or_404(Work, id=work_id)
        user = get_object_or_404(User, username=username)
        target = get_object_or_404(User, username=targetname)
        if Rating.objects.filter(user=target, work=work,
                                 choice__in=['favorite', 'like', 'neutral', 'dislike']).count() == 0 and (
                    request.user == user or request.user == target):
            Recommendation.objects.get(work=work, user=user, target_user=target).delete()

        return HttpResponse()
    else:
        raise Http404


def remove_all_reco(request, targetname):
    if request.method == 'POST':
        target = get_object_or_404(User, username=targetname)
        if target == request.user:
            reco_list = Recommendation.objects.filter(target_user=target)
            for reco in reco_list:
                if Rating.objects.filter(user=request.user, work=reco.work,
                                         choice__in=['favorite', 'like', 'neutral', 'dislike']).count() == 0:
                    reco.delete()

        return HttpResponse()
    else:
        raise Http404


def get_reco(request):
    category = request.GET.get('category', 'all')
    algo_name = request.GET.get('algo', 'als')
    merge_type = request.GET.get('merge_type', 'intersection')
    group_reco = None
    if request.user.is_authenticated:
        group_reco = request.session.setdefault(
            settings.RECO_GROUP_SESSION_KEY, [request.user.username]
        )
    NB_RECO = 9
    if current_user_ratings(request):
        reco_list = [{
            'work': Work(title='Chargement…', ext_poster='/static/img/chiro.gif')
        } for _ in range(NB_RECO)]
    else:
        reco_list = []
    return render(request, 'mangaki/reco_list.html',
                  {
                      'reco_list': reco_list,
                      'category': category,
                      'algo_name': algo_name,
                      'merge_type': merge_type,
                      'group_reco': group_reco,
                      'config': VANILLA_UI_CONFIG_FOR_RATINGS
                  })


def update_settings(request):
    is_ok = None
    if request.method == 'POST':  # Confirmed from mail link
        is_ok = 'yes' in request.POST
        username = request.POST.get('username')
        token = request.POST.get('token')
    elif request.method == 'GET':  # Clicked on mail link
        username = request.GET.get('username')
        token = request.GET.get('token')
    expected_token = compute_token(NEWS_SALT, username)
    if not constant_time_compare(token, expected_token):
        # If the token is invalid, add an error message
        messages.error(request,
            'Vous n\'êtes pas autorisé à effectuer cette action.')
        return render(request, 'settings.html', status=401)  # Unauthorized
    elif is_ok is not None:
        message = 'Votre profil a bien été mis à jour. '
        if is_ok:
            message += 'Profitez bien de Mangaki !'
        else:
            message += 'Vous ne recevrez plus de mails de notre part.'
        Profile.objects.filter(
            user__username=username).update(newsletter_ok=is_ok)
        messages.success(request, message)
        return render(request, 'settings.html')
    return render(request, 'settings.html', {'username': username,
                                             'token': token})


def add_pairing(request, artist_id, work_id):
    if request.user.is_authenticated:
        artist = get_object_or_404(Artist, id=artist_id)
        work = get_object_or_404(Work, id=work_id)
        Pairing(user=request.user, artist=artist, work=work).save()
    return HttpResponse()


def faq_index(request):
    latest_theme_list = FAQTheme.objects.order_by('order')
    all_information = [[faqtheme.theme, [(entry.question, entry.answer) for entry in
                                         faqtheme.entries.filter(is_active=True).order_by('-pub_date')]] for faqtheme in
                       latest_theme_list]
    context = {
        'information': all_information,
    }
    return render(request, 'faq/faq_index.html', context)


def legal_mentions(request):
    return render(request, 'mangaki/legal.html')


def fix_index(request):
    suggestion_list = Suggestion.objects.select_related('work', 'user').prefetch_related(
        'work__category', 'evidence_set__user').annotate(
            count_agrees=Count(Case(When(evidence__agrees=True, then=1))),
            count_disagrees=Count(Case(When(evidence__agrees=False, then=1)))
        ).all().order_by('is_checked', '-date')

    paginator = Paginator(suggestion_list, FIXES_PER_PAGE)
    page = request.GET.get('page')

    try:
        suggestions = paginator.page(page)
    except PageNotAnInteger:
        suggestions = paginator.page(1)
    except EmptyPage:
        suggestions = paginator.page(paginator.num_pages)

    context = {
        'suggestions': suggestions
    }

    return render(request, 'fix/fix_index.html', context)


def fix_suggestion(request, suggestion_id):
    cluster_colors = {
        'unprocessed': 'text-info',
        'accepted': 'text-success',
        'rejected': 'text-danger'
    }

    # Retrieve the Suggestion object if it exists else raise a 404 error
    suggestion = get_object_or_404(
        Suggestion.objects.select_related('work', 'user', 'work__category').annotate(
            count_agrees=Count(Case(When(evidence__agrees=True, then=1))),
            count_disagrees=Count(Case(When(evidence__agrees=False, then=1)))
        ),
        id=suggestion_id
    )

    # Retrieve the Evidence object if it exists
    evidence = None
    if request.user.is_authenticated:
        try:
            evidence = Evidence.objects.get(user=request.user, suggestion=suggestion)
        except ObjectDoesNotExist:
            evidence = None

    # Retrieve related clusters
    clusters = WorkCluster.objects.select_related(
        'resulting_work', 'resulting_work__category').prefetch_related(
        'works', 'works__category', 'checker').filter(origin=suggestion_id).all()
    colors = [cluster_colors[cluster.status] for cluster in clusters]

    # Get the previous suggestion, ie. more recent and of the same checked status
    previous_suggestions_ids = Suggestion.objects.filter(date__gt=suggestion.date,
        is_checked=suggestion.is_checked).order_by('date').values_list('id', flat=True)

    # If there is no more recent suggestion, and was checked, just pick from not checked suggestions
    if not previous_suggestions_ids and suggestion.is_checked:
        previous_suggestions_ids = Suggestion.objects.filter(is_checked=False).order_by('date').values_list('id', flat=True)

    # Get the next suggestion, ie. less recent and of the same checked status
    next_suggestions_ids = Suggestion.objects.filter(date__lt=suggestion.date,
        is_checked=suggestion.is_checked).order_by('-date').values_list('id', flat=True)

    # If there is no less recent suggestion, and wasn't checked, just pick from checked suggestions
    if not next_suggestions_ids and not suggestion.is_checked:
        next_suggestions_ids = Suggestion.objects.filter(is_checked=True).order_by('-date').values_list('id', flat=True)

    context = {
        'suggestion': suggestion,
        'clusters': zip(clusters, colors) if clusters and colors else None,
        'evidence': evidence,
        'can_auto_fix': suggestion.can_auto_fix and request.user.is_staff,
        'can_close': request.user.is_staff,
        'can_reopen': request.user.is_staff,
        'next_id': next_suggestions_ids[0] if next_suggestions_ids else None,
        'previous_id': previous_suggestions_ids[0] if previous_suggestions_ids else None
    }

    return render(request, 'fix/fix_suggestion.html', context)


def nsfw_grid(request):
    user = request.user if request.user.is_authenticated else None

    user_evidences = Evidence.objects.filter(user=user)
    nsfw_suggestion_list = Suggestion.objects.select_related(
                'work', 'user', 'work__category'
            ).prefetch_related('evidence_set__user').filter(
                problem__in=('nsfw', 'n_nsfw'),
                is_checked=False
            ).exclude(
                work__in=user_evidences.values('suggestion__work')
            ).order_by('work', '-date', '-work__sum_ratings').distinct('work')

    paginator = Paginator(nsfw_suggestion_list, NSFW_GRID_PER_PAGE)
    count_nsfw_left = paginator.count
    page = request.GET.get('page')

    try:
        suggestions = paginator.page(page)
    except PageNotAnInteger:
        suggestions = paginator.page(1)
    except EmptyPage:
        suggestions = paginator.page(paginator.num_pages)

    nsfw_states = []
    supposed_nsfw = []
    for suggestion in suggestions:
        supposed_nsfw.append(suggestion.problem == 'nsfw')

        for evidence in suggestion.evidence_set.all():
            if evidence.user == request.user:
                agrees_with_problem = evidence.agrees
                agrees = ((agrees_with_problem and suggestion.problem == 'nsfw')
                       or (not agrees_with_problem and not suggestion.problem == 'nsfw'))
                nsfw_states.append(agrees)
                break
        else:
            nsfw_states.append(None)

    suggestions_with_states = list(zip(suggestions, nsfw_states, supposed_nsfw))

    context = {
        'suggestions_with_states': suggestions_with_states,
        'suggestions': suggestions,
        'count_nsfw_left': count_nsfw_left
    }

    return render(request, 'fix/nsfw_grid.html', context)


@login_required
def update_evidence(request):
    if request.method != 'POST' or not request.user.is_authenticated:
        return redirect('fix-index')

    # Retrieve agrees, needs_help, delete and suggestion_ids values from one or several fields in a form
    # Every values are then zipped together, with zip_longest since the length of suggestion_ids is the one that matters
    # See templates/fix/nsfw_grid.html for an example
    agrees_values = map(lambda x: x == 'True', request.POST.getlist('agrees'))
    needs_help_values = map(lambda x: x == 'True', request.POST.getlist('needs_help'))
    delete_values = request.POST.getlist('delete')
    suggestion_ids = map(int, request.POST.getlist('suggestion'))
    close_values = map(lambda x: x == 'True', request.POST.getlist('close_suggestion'))
    reopen_values = map(lambda x: x == 'True', request.POST.getlist('re_open'))
    auto_fix_values = map(lambda x: x == 'True', request.POST.getlist('auto_fix'))

    informations = zip_longest(
        suggestion_ids,
        agrees_values,
        needs_help_values,
        delete_values,
        close_values,
        reopen_values,
        auto_fix_values,
        fillvalue=False)

    for suggestion_id, agrees, needs_help, delete, close, reopen, auto_fix in informations:
        if not suggestion_id:
            continue

        if delete:
            try:
                Evidence.objects.get(
                    user=request.user,
                    suggestion=Suggestion.objects.get(pk=suggestion_id)
                ).delete()
            except ObjectDoesNotExist:
                pass
        elif close:
            try:
               Suggestion.objects.filter(pk=suggestion_id).update(is_checked=True)
            except ObjectDoesNotExist:
                pass
        elif reopen:
            try:
                Suggestion.objects.filter(pk=suggestion_id).update(is_checked=False)
            except ObjectDoesNotExist:
                pass
        elif auto_fix:
            try:
                suggestion = Suggestion.objects.get(pk=suggestion_id)
                suggestion.auto_fix()
            except ObjectDoesNotExist:
                pass
            except ValueError:
                pass
        else:
            evidence, created = Evidence.objects.get_or_create(
                user=request.user,
                suggestion=Suggestion.objects.get(pk=suggestion_id)
            )
            evidence.agrees = agrees
            evidence.needs_help = needs_help
            evidence.save()

    next_url = request.GET.get('next')
    if next_url and is_safe_url(url=next_url, allowed_hosts=request.get_host()):
        return redirect(next_url)
    return redirect('fix-index')


def generic_error_view(error, error_code):
    def error_view(request, exception=None):
        try:
            trope = Trope.objects.order_by('?').first()
        except DatabaseError:
            return server_error(request)

        parameters = {
            'error_code': error_code,
            'error': error,
        }
        if trope:
            parameters['trope'] = trope
            parameters['origin'] = trope.origin
        return render(request, 'error.html', parameters, status=error_code)

    return error_view


class AnonymousRatingsMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ratings = get_anonymous_ratings(self.request.session)
        works = (
            Work.objects.filter(id__in=ratings)
                .order_by('title')
                .group_by_category()
        )
        categories = Category.objects.filter(id__in=works).in_bulk()
        # Build the tree of ratings. This is a list of pairs (category, works)
        # where category is a Category object and works is the list of ratings
        # for objects of this category. works itself is a list of dictionnaries
        # {'work', 'choice'} where the 'work' key corresponds to the Work
        # object that was rated and 'choice' corresponds to the rating.
        #
        # Example:
        # [
        # (anime_category, [{'choice': 'like', 'work': Work()}, {'choice': 'dislike', 'work': Work()}]),
        # (manga_ategory, [{'choice': 'like', 'work': Work()}])
        # ]
        context['ratings'] = [
            (categories[category_id], [
                {'choice': ratings[work.id], 'work': work}
                for work in works_list
            ])
            for category_id, works_list in works.items()
        ]
        context['meta'] = {'config': VANILLA_UI_CONFIG_FOR_RATINGS}  
        return context


class SignupView(AnonymousRatingsMixin, allauth.account.views.SignupView):
    pass


signup = SignupView.as_view()


class LoginView(AnonymousRatingsMixin, allauth.account.views.LoginView):
    pass


login = LoginView.as_view()


def deleted_account(request):
    return render(request, 'account/account_deleted.html')
