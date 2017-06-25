import datetime
import json
from collections import Counter, OrderedDict
from urllib.parse import urlencode

import allauth.account.views

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import SuspiciousOperation
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import DatabaseError
from django.db.models import Case, IntegerField, Sum, Value, When
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.timezone import utc
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.defaults import server_error
from django.views.generic import View
from django.views.generic.detail import DetailView, SingleObjectMixin, SingleObjectTemplateResponseMixin
from django.views.generic.edit import FormMixin
from django.views.generic.list import ListView
from markdown import markdown
from natsort import natsorted

from irl.models import Attendee, Event, Partner
from mangaki.choices import TOP_CATEGORY_CHOICES
from mangaki.forms import SuggestionForm
from mangaki.mixins import AjaxableResponseMixin, JSONResponseMixin
from mangaki.models import (Artist, Category, ColdStartRating, FAQTheme, Page, Pairing, Profile, Ranking, Rating,
                            Recommendation, Staff, Suggestion, Top, Trope, Work)
from mangaki.utils.mal import import_mal, client
from mangaki.utils.ratings import (clear_anonymous_ratings, current_user_rating, current_user_ratings,
                                   current_user_set_toggle_rating, get_anonymous_ratings)
from mangaki.utils.algo import get_algo_backup, get_dataset_backup
from mangaki.utils.tokens import compute_token, KYOTO_SALT
from mangaki.utils.recommendations import get_reco_algo, user_exists_in_backup, get_pos_of_best_works_for_user_via_algo
from irl.models import Event, Partner, Attendee


NB_POINTS_DPP = 10
POSTERS_PER_PAGE = 24
TITLES_PER_PAGE = 24
USERNAMES_PER_PAGE = 24
REFERENCE_DOMAINS = (
    ('http://myanimelist.net', 'myAnimeList'),
    ('http://animeka.com', 'Animeka'),
    ('http://vgmdb.net', 'VGMdb'),
    ('http://anidb.net', 'AniDB'),
    ('https://anidb.net', 'AniDB')
)

RATING_COLORS = {
    'favorite': {'normal': '#f8d549', 'highlight': '#f8d549'},
    'like': {'normal': '#5cb85c', 'highlight': '#47a447'},
    'neutral': {'normal': '#f0ad4e', 'highlight': '#ec971f'},
    'dislike': {'normal': '#d9534f', 'highlight': '#c9302c'},
    'willsee': {'normal': '#337ab7', 'highlight': '#286090'},
    'wontsee': {'normal': '#5bc0de', 'highlight': '#31b0d5'}
}

UTA_ID = 14293


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

        context['genres'] = ', '.join(genre.title for genre in self.object.genre.all())

        if self.request.user.is_authenticated:
            context['suggestion_form'] = SuggestionForm(instance=Suggestion(user=self.request.user, work=self.object))
        context['rating'] = current_user_rating(self.request, self.object)

        context['references'] = []
        for reference in self.object.reference_set.all():
            for domain, name in REFERENCE_DOMAINS:
                if reference.url.startswith(domain):
                    context['references'].append((reference.url, name))

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

        events = self.object.event_set \
            .filter(date__gte=timezone.now()) \
            .annotate(nb_attendees=Sum(Case(
            When(attendee__attending=True, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )))
        if len(events) > 0:
            my_events = {}
            if self.request.user.is_authenticated:
                my_events = dict(self.request.user.attendee_set.filter(
                    event__in=events).values_list('event_id', 'attending'))

            context['events'] = [
                {
                    'id': event.id,
                    'attending': my_events.get(event.id, None),
                    'type': event.get_event_type_display(),
                    'channel': event.channel,
                    'date': event.get_date(),
                    'link': event.link,
                    'location': event.location,
                    'nb_attendees': event.nb_attendees,
                } for event in events
            ]

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


class EventDetail(LoginRequiredMixin, DetailView):
    model = Event

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'next' in request.GET:
            return redirect(request.GET['next'])
        return redirect(self.object.work.get_absolute_url())

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
                defaults={'attending': attending})
        elif 'cancel' in request.POST:
            Attendee.objects.filter(event=self.object, user=request.user).delete()
        return redirect(request.GET['next'])


class CardList(JSONResponseMixin, ListView):
    model = Work

    def get_queryset(self):
        category = self.kwargs.get('category')
        # This call to `int` shouldn't fail because `sort_id` must match the
        # `\d+` regexp, cf urls.py.
        sort_id = int(self.kwargs.pop('sort_id'))
        if sort_id < 1 or sort_id > 5:
            raise Http404
        deja_vu = self.request.GET.get('dejavu', '').split(',')
        sort_mode = ['popularity', 'controversy', 'top', 'random', 'dpp'][int(sort_id) - 1]
        queryset = Category.objects.get(slug=category).work_set.all()
        if sort_mode == 'popularity':
            queryset = queryset.popular()
        elif sort_mode == 'controversy':
            queryset = queryset.controversial()
        elif sort_mode == 'top':
            queryset = queryset.top()
        elif sort_mode == 'random':
            queryset.random().order_by('?')
        else:
            queryset = queryset.dpp(NB_POINTS_DPP)
        rated_works = current_user_ratings(self.request)
        queryset = queryset.exclude(id__in=list(rated_works))
        return queryset[:POSTERS_PER_PAGE]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cards = []
        for work in context['object_list']:
            cards.append({
                'id': work.id,
                'category': work.category.slug,
                'title': work.title,
                'poster': work.safe_poster(self.request.user),
                'synopsis': work.synopsis,
                'nsfw': work.nsfw
            })
        return {'cards': cards}

    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)


class WorkListMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ratings = current_user_ratings(
            self.request, list(context['object_list']))
        for work in context['object_list']:
            work.rating = ratings.get(work.id, None)

        return context


@method_decorator(ensure_csrf_cookie, name='dispatch')
class WorkList(WorkListMixin, ListView):
    paginate_by = POSTERS_PER_PAGE

    @cached_property
    def category(self):
        return get_object_or_404(Category, slug=self.kwargs.get('category'))

    def search(self):
        return self.request.GET.get('search', None)

    def sort_mode(self):
        default = 'mosaic'
        sort = self.request.GET.get('sort', default)
        if self.search() is not None and sort == default:
            return 'popularity'  # Mosaic cannot be searched through because it is random. We enforce the popularity as the second default when searching.
        else:
            return sort

    @property
    def is_dpp(self):
        return self.kwargs.get('dpp', False)

    def get_queryset(self):
        search_text = self.search()
        queryset = self.category.work_set.all()
        sort_mode = self.sort_mode()
        if self.is_dpp:
            queryset = self.category.work_set.exclude(coldstartrating__user=self.request.user).dpp(10)
        elif sort_mode == 'top':
            queryset = queryset.top()
        elif sort_mode == 'popularity':
            queryset = queryset.popular()
        elif sort_mode == 'controversy':
            queryset = queryset.controversial()
        elif sort_mode == 'alpha':
            letter = self.request.GET.get('letter', '0')
            if letter == '0':  # '#'
                queryset = queryset.exclude(title__regex=r'^[a-zA-Z]')
            else:
                queryset = queryset.filter(title__istartswith=letter)
            queryset = queryset.order_by('title')
        elif sort_mode == 'random':
            queryset = queryset.random().order_by('?')[:self.paginate_by]
        elif sort_mode == 'mosaic':
            queryset = queryset.none()
        else:
            raise Http404

        if search_text is not None:
            queryset = queryset.search(search_text)

        queryset = queryset.only('pk', 'title', 'int_poster', 'ext_poster', 'nsfw', 'synopsis', 'category__slug')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_text = self.search()
        sort_mode = self.sort_mode()

        context['search'] = search_text
        context['sort_mode'] = sort_mode
        context['letter'] = self.request.GET.get('letter', '')
        context['category'] = self.category.slug
        context['objects_count'] = self.category.work_set.count()
        context['is_dpp'] = self.is_dpp

        if sort_mode == 'mosaic' and not self.is_dpp:
            context['object_list'] = [
                Work(title='Chargement…', ext_poster='/static/img/chiro.gif')
                for _ in range(4)
            ]

        return context


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

        return context


def get_profile(request, username=None):
    if username is None and request.user.is_authenticated():
        return redirect('profile', request.user.username, permanent=True)

    is_anonymous = False
    if username:
        user = get_object_or_404(User, username=username)
    else:
        user = request.user
        is_anonymous = not request.user.is_authenticated()

    is_shared = is_anonymous or (username is None) or user == request.user or user.profile.is_shared
    category = request.GET.get('category', 'anime')
    algo_name = request.GET.get('algo', None)
    categories = ('anime', 'manga', 'album')
    ordering = ['favorite', 'willsee', 'like', 'neutral', 'dislike', 'wontsee']
    if is_anonymous:
        ratings = []
        anon_ratings = get_anonymous_ratings(request.session)
        works_per_pk = Work.objects.select_related('category').in_bulk(anon_ratings.keys())
        for pk, choice in anon_ratings.items():
            rating = Rating()
            rating.work = works_per_pk[pk]
            rating.choice = choice
            ratings.append(rating)
    else:
        ratings = list(
            Rating.objects
            .filter(user__username=username)
            .select_related('work', 'work__category')
        )

    compare_function = lambda x: (ordering.index(x.choice), x.work.title.lower())  # By default, sort by rating then name
    if algo_name is not None:
        try:
            work_ids = [rating.work_id for rating in ratings]
            algo = get_algo_backup(algo_name)
            dataset = get_dataset_backup(algo_name)
            best_pos = get_pos_of_best_works_for_user_via_algo(algo, dataset, user.id, work_ids)
            ranking = {}
            for rank, pos in enumerate(best_pos):
                ranking[ratings[pos].id] = rank
            compare_function = lambda x: (ordering.index(x.choice), ranking[x.id])
        except:  # Two possible reasons: no backup or user not in backup
            pass

    rating_list = natsorted(ratings, key=compare_function)

    received_recommendation_list = []
    sent_recommendation_list = []
    if not is_anonymous and category == 'recommendation':
        received_recommendations = Recommendation.objects.filter(target_user__username=username).select_related('work',
                                                                                                                'work__category')
        sent_recommendations = Recommendation.objects.filter(user__username=username).select_related('work',
                                                                                                     'work__category')
        for reco in received_recommendations:
            if Rating.objects.filter(work=reco.work, user__username=username,
                                     choice__in=['favorite', 'like', 'neutral', 'dislike']).count() == 0:
                received_recommendation_list.append(
                    {'category': reco.work.category.slug, 'id': reco.work.id, 'title': reco.work.title,
                     'username': reco.user.username})
        for reco in sent_recommendations:
            if Rating.objects.filter(work=reco.work, user=reco.target_user,
                                     choice__in=['favorite', 'like', 'neutral', 'dislike']).count() == 0:
                sent_recommendation_list.append(
                    {'category': reco.work.category.slug, 'id': reco.work.id, 'title': reco.work.title,
                     'username': reco.target_user.username})

    # FIXME: if we don't show 4 lists out of 6, we should never fetch / create them from the start.
    seen_lists = {key: [] for key in categories}
    unseen_lists = {key: [] for key in categories}
    for r in rating_list:
        if r.choice in ['favorite', 'like', 'neutral', 'dislike']:
            seen_lists[r.work.category.slug].append(r)
        else:
            unseen_lists[r.work.category.slug].append(r)

    member_time = None
    if not is_anonymous:
        member_time = datetime.datetime.now().replace(tzinfo=utc) - user.date_joined

    # Events
    events = []
    if not is_anonymous:
        events = [
            {
                'id': attendee.event_id,
                'work_id': attendee.event.work_id,
                'attending': True,
                'type': attendee.event.get_event_type_display(),
                'channel': attendee.event.channel,
                'date': attendee.event.get_date(),
                'link': attendee.event.link,
                'location': attendee.event.location,
                'title': attendee.event.work.title,
            } for attendee in
            user.attendee_set.filter(event__date__gte=timezone.now(), attending=True).select_related('event',
                                                                                                     'event__work')
        ]

    data = {
        'is_mal_import_available': client.is_available,
        'username': username,
        'is_shared': is_shared,
        'category': category,
        'avatar_url': user.profile.avatar_url if not is_anonymous else None,
        'member_days': member_time.days if member_time else None,
        'anime_count': len(seen_lists['anime']),
        'manga_count': len(seen_lists['manga']),
        'reco_count': len(received_recommendation_list),
        'seen_list': seen_lists.get(category, []) if is_shared else [],
        'unseen_list': unseen_lists.get(category, []) if is_shared else [],
        'received_recommendation_list': received_recommendation_list if is_shared else [],
        'sent_recommendation_list': sent_recommendation_list if is_shared else [],
        'events': events,
        'is_anonymous': is_anonymous,
        'show_all_categories': is_anonymous,
        'ratings_disabled': request.user.username != username and not is_anonymous,
        'categories': [(category, seen_lists.get(category, []), unseen_lists.get(category, []))
                       for category in categories],
    }
    return render(request, 'profile.html', data)


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


def about(request):
    return render(request, 'about.html')


def events(request):
    uta_rating = None
    if request.user.is_authenticated:
        for rating in Rating.objects.filter(work_id=UTA_ID, user=request.user):
            if rating.work_id == UTA_ID:
                uta_rating = rating.choice
    utamonogatari = Work.objects.in_bulk([UTA_ID])
    return render(
        request, 'events.html',
        {
            'screenings': Event.objects.filter(event_type='screening', date__gte=timezone.now()),
            'utamonogatari': utamonogatari.get(UTA_ID, None),
            'wakanim': Partner.objects.get(pk=12),
            'utamonogatari_rating': uta_rating,
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


# FIXME @login_required
def dpp_work(request, work_id):
    if request.user.is_authenticated() and request.method == 'POST':
        work = get_object_or_404(Work, id=work_id)
        choice = request.POST.get('choice', '')
        if choice not in ['like', 'dislike', 'dontknow']:
            raise SuspiciousOperation(
                "Attempted access denied. There are only 3 ratings here: like, dislike and dontknow")
        ColdStartRating.objects.update_or_create(user=request.user, work=work, defaults={'choice': choice})
        return HttpResponse(choice)
    else:
        raise Http404


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


def get_reco_algo_list(request, algo, category):
    reco_list = []
    data = get_reco_algo(request, algo, category)
    works = data['works']
    for work_id in data['work_ids']:
        work = works[work_id]
        reco_list.append({'id': work.id, 'title': work.title, 'poster': work.ext_poster, 'synopsis': work.synopsis,
                          'category': work.category.slug})
    return HttpResponse(json.dumps(reco_list), content_type='application/json')


def get_reco_list_dpp(request, category):
    reco_list_dpp = []
    data = get_reco_algo(request, 'knn', category)
    works = data['works']
    for work_id in data['work_ids']:
        work = works[work_id]
        reco_list_dpp.append({'id': work.id, 'title': work.title, 'poster': work.ext_poster, 'synopsis': work.synopsis,
                              'category': work.category.slug})
    return HttpResponse(json.dumps(reco_list_dpp), content_type='application/json')


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
    algo_name = request.GET.get('algo', 'svd' if user_exists_in_backup(request.user, 'svd') else 'knn')
    if current_user_ratings(request):
        reco_list = [Work(title='Chargement…', ext_poster='/static/img/chiro.gif') for _ in range(4)]
    else:
        reco_list = []
    return render(request, 'mangaki/reco_list.html', {'reco_list': reco_list, 'category': category, 'algo': algo_name})


def get_reco_dpp(request):
    category = request.GET.get('category', 'all')
    reco_list = [Work(title='Chargement…', ext_poster='/static/img/chiro.gif') for _ in range(4)]
    return render(request, 'mangaki/reco_list_dpp.html', {'reco_list': reco_list, 'category': category})


def update_shared(request):
    if request.user.is_authenticated and request.method == 'POST':
        Profile.objects.filter(user=request.user).update(is_shared=request.POST['is_shared'] == 'true')
    return HttpResponse()


def update_nsfw(request):
    if request.user.is_authenticated and request.method == 'POST':
        Profile.objects.filter(user=request.user).update(nsfw_ok=request.POST['nsfw_ok'] == 'true')
    return HttpResponse()


def update_newsletter(request):
    if request.user.is_authenticated and request.method == 'POST':
        Profile.objects.filter(user=request.user).update(newsletter_ok=request.POST['newsletter_ok'] == 'true')
    return HttpResponse()


def update_research(request):
    is_ok = None
    if request.user.is_authenticated and request.method == 'POST' and 'research_ok' in request.POST:  # Toggle on one's profile
        username = request.user.username
        is_ok = request.POST.get('research_ok') == 'true'
        Profile.objects.filter(user__username=username).update(research_ok=is_ok)
        return HttpResponse()
    if request.method == 'POST':  # Confirmed from mail link
        is_ok = 'yes' in request.POST
        username = request.POST.get('username')
        token = request.POST.get('token')
    elif request.method == 'GET':  # Clicked on mail link
        username = request.GET.get('username')
        token = request.GET.get('token')
    expected_token = compute_token(KYOTO_SALT, username)
    if not constant_time_compare(token, expected_token):  # If the token is invalid
        # Add an error message
        messages.error(request, 'Vous n\'êtes pas autorisé à effectuer cette action.')
        return render(request, 'research.html', status=401)  # Unauthorized
    elif is_ok is not None:
        message = 'Votre profil a bien été mis à jour. '
        if is_ok:
            message += 'Merci. Vos données seront présentes dans le data challenge de Kyoto.'
        else:
            message += 'Vos données ne feront pas partie du data challenge de Kyoto.'
        Profile.objects.filter(user__username=username).update(research_ok=is_ok)
        messages.success(request, message)
        return render(request, 'research.html')
    return render(request, 'research.html', {'username': username, 'token': token})


def update_reco_willsee(request):
    if request.user.is_authenticated and request.method == 'POST':
        Profile.objects.filter(user=request.user).update(reco_willsee_ok=request.POST['reco_willsee_ok'] == 'true')
    return HttpResponse()


def import_from_mal(request, mal_username):
    if request.method == 'POST' and client.is_available:
        nb_added, fails = import_mal(mal_username, request.user.username)
        payload = {
            'added': nb_added,
            'failures': fails
        }
        return HttpResponse(json.dumps(payload), content_type='application/json')
    elif not client.is_available:
        raise Http404()
    else:
        return HttpResponse()


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


def generic_error_view(error, error_code):
    def error_view(request):
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
        return context


class SignupView(AnonymousRatingsMixin, allauth.account.views.SignupView):
    pass


signup = SignupView.as_view()


class LoginView(AnonymousRatingsMixin, allauth.account.views.LoginView):
    pass


login = LoginView.as_view()
