from django.shortcuts import render
from django.http import HttpResponse

from profiles.models import Profile


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


def update_reco_willsee(request):
    if request.user.is_authenticated and request.method == 'POST':
        Profile.objects.filter(user=request.user).update(reco_willsee_ok=request.POST['reco_willsee_ok'] == 'true')
    return HttpResponse()

