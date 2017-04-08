from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from profiles.models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
