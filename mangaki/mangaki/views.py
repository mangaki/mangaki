from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.shortcuts import render, redirect, get_object_or_404
from mangaki.models import Anime
import datetime
import random

class AnimeDetailView(DetailView):
    model = Anime

def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

"""def save_answer(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    Session(user=request.user, item=item, answer=request.POST['answer'], end=datetime.datetime.now()).save()
    return redirect('/item/%d' % random.randint(1, 83))
"""
