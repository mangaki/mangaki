from django.db import models
from django.conf import settings

from mangaki.models import Rating


class Profile(models.Model):
    class Meta:
        db_table = 'mangaki_profile'

    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE)
    is_shared = models.BooleanField(default=True)
    nsfw_ok = models.BooleanField(default=False)
    newsletter_ok = models.BooleanField(default=True)
    reco_willsee_ok = models.BooleanField(default=False)
    avatar_url = models.CharField(max_length=128, default='', blank=True, null=True)
    mal_username = models.CharField(max_length=64, default='', blank=True, null=True)

    def get_anime_count(self):
        return Rating.objects.filter(user=self.user, choice__in=['like', 'neutral', 'dislike', 'favorite']).count()
