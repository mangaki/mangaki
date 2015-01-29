from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, Http404
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added
from mangaki.models import Work, Anime, Rating, Page, Profile, Artist
from collections import Counter
from markdown import markdown
from secret import DISCOURSE_API_USERNAME, DISCOURSE_API_KEY, MAL_USER, MAL_PASS
from pydiscourse.client import DiscourseClient
from urllib.request import urlopen
import xml.etree.ElementTree as ET
import datetime
import requests
import random
import json
import html
import re

class AnimeDetail(DetailView):
    model = Anime
    def get_context_data(self, **kwargs):
        context = super(AnimeDetail, self).get_context_data(**kwargs)
        if self.object.nsfw:
            context['object'].poster = '/static/img/nsfw.jpg'  # NSFW
        context['object'].source = context['object'].source.split(',')[0]
        if self.request.user.is_authenticated():
            try:
                context['rating'] = self.object.rating_set.get(user=self.request.user).choice
            except Rating.DoesNotExist:
                pass
        return context

class AnimeList(ListView):
    model = Anime
    context_object_name = 'anime'
    def get_queryset(self):
        return Anime.objects.order_by('title') if 'alpha' in self.kwargs['mode'] else Anime.objects.all()[:24]
    def get_context_data(self, **kwargs):
        context = super(AnimeList, self).get_context_data(**kwargs)
        context['mode'] = self.kwargs['mode']
        context['anime_count'] = Anime.objects.count()
        context['template_mode'] = 'work_no_poster.html' if 'flat' in self.kwargs['mode'] else 'work_poster.html'
        if self.request.user.is_authenticated():
            for obj in context['object_list']:
                if obj.nsfw:
                    obj.poster = '/static/img/nsfw.jpg'  # NSFW
                try:
                    obj.rating = obj.rating_set.get(user=self.request.user).choice
                except Rating.DoesNotExist:
                    pass
        return context 

def get_discourse_data(email):
    client = DiscourseClient('http://meta.mangaki.fr', api_username=DISCOURSE_API_USERNAME, api_key=DISCOURSE_API_KEY)
    try:
        users = client._get('/admin/users/list/active.json?show_emails=true')
        for user in users:
            if user['email'] == email:
                return {'avatar': 'http://meta.mangaki.fr' + user['avatar_template'], 'created_at': user['created_at']}
        return {'avatar': '/static/img/unknown.png', 'created_at': datetime.datetime.now().isoformat() + 'Z'}
    except:
        return {'avatar': '/static/img/unknown.png', 'created_at': datetime.datetime.now().isoformat() + 'Z'}

def get_profile(request, username):
    try:
        is_shared = Profile.objects.get(user__username=username).is_shared
    except Profile.DoesNotExist:
        Profile(user=request.user).save()  # À supprimer à terme
        is_shared = True
    ordering = ['willsee', 'like', 'neutral', 'dislike', 'wontsee']
    seen_list = sorted(Rating.objects.filter(user__username=username, choice__in=['like', 'neutral', 'dislike']), key=lambda x: (ordering.index(x.choice), x.work.title))
    unseen_list = sorted(Rating.objects.filter(user__username=username, choice__in=['willsee', 'wontsee']), key=lambda x: (ordering.index(x.choice), x.work.title))
    discourse_data = get_discourse_data(User.objects.get(username=username).email)
    member_time = datetime.datetime.now() - datetime.datetime.strptime(discourse_data['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
    return render(request, 'profile.html', {
        'username': username,
        'is_shared': is_shared,
        'avatar_url': discourse_data['avatar'].format(size=150),
        'member_days': member_time.days,
        'anime_count': len(seen_list),
        'seen_list': seen_list if is_shared else [],
        'unseen_list': unseen_list if is_shared else []
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
        work = get_object_or_404(Work, id=work_id)
        Rating.objects.update_or_create(user=request.user, work=work, defaults={'choice': request.POST['choice']})
        return HttpResponse(request.POST['choice'])
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
            anime = Anime.objects.create(director=unknown, composer=unknown, title=title, source='http://myanimelist.net/anime/' + entry['id'], poster=entry['image'], date=anime_date)
    if redirect:
        return get_works(request, 'anime', query)

def get_recommendations(user):
    contest = []
    values = {'like': 2, 'dislike': -2, 'neutral': 0.1, 'willsee': 0.5, 'wontsee': -0.5}
    neighbors = Counter()
    for my in Rating.objects.filter(user=user):
        for her in Rating.objects.filter(work=my.work):
            neighbors[her.user.id] = values[my.choice] * values[her.choice]
    works = Counter()
    nb_ratings = {}
    for user_id, score in neighbors.most_common(10):
        for her in Rating.objects.filter(user__id=user_id):
            if her.work.id not in works:
                works[her.work.id] = [values[her.choice], neighbors[her.user.id]]
                nb_ratings[her.work.id] = 1
            else:
                works[her.work.id][0] += values[her.choice]
                works[her.work.id][1] += score
                nb_ratings[her.work.id] += 1
    for work_id in works:
        if nb_ratings[work_id] == 1 or (Rating.objects.filter(user=user, work__id=work_id).count() != 0 and Rating.objects.filter(user=user, work__id=work_id, choice='willsee').count() == 0):
            works[work_id] = (0, 0)
        else:
            # print(Work.objects.get(id=work_id).title, Rating.objects.filter(user=user, work__id=work_id).count(), )
            works[work_id] = (float(works[work_id][0]) / nb_ratings[work_id], works[work_id][1])
    return works.most_common(4)

@login_required
def get_reco(request):
    reco_list = []
    for work_id, _ in get_recommendations(request.user):
        reco = Anime.objects.get(id=work_id)
        if Rating.objects.filter(user=request.user, work__id=work_id).count() != 0:
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

"""def lookup_work(request):
    query = request.POST.get('query', False)
    get_extra_works(request, query, False)
    return HttpResponse(1)"""

def report_nsfw(request, pk):
    Anime.objects.filter(id=pk).update(nsfw=True)
    return redirect('/anime/%s' % pk)

@receiver(user_signed_up)
@receiver(social_account_added)
def register_profile(sender, **kwargs):
    request = kwargs['request']
    user = kwargs['user']
    Profile(user=user).save()
