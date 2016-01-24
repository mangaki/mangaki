from django.db import models
from mangaki.models import Anime
from django.contrib.auth.models import User
import locale


class Location(models.Model):
    title = models.CharField(max_length=64, verbose_name='Titre')
    address = models.TextField(verbose_name='Adresse')
    postal_code = models.CharField(max_length=5, verbose_name='Code postal')
    city = models.CharField(max_length=64, verbose_name='Ville')

    def __str__(self):
        return '%s, %s' % (self.title, self.city)

class Attendee(models.Model):
    event = models.ForeignKey('Event', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    attending = models.BooleanField(default=False)

class Event(models.Model):
    anime = models.ForeignKey(Anime)
    location = models.ForeignKey('Location', blank=True, null=True)
    event_type = models.CharField(max_length=9, choices=(
        ('premiere', 'avant-première'),
        ('screening', 'projection'),
        ('release', 'sortie'),
        ('tv', 'diffusion')
    ))
    language = models.CharField(max_length=6, choices=(
        ('vf', 'VF'),
        ('vostfr', 'VOSTFR'),
        ('vosta', 'VOSTA'),
    ))
    channel = models.CharField(max_length=16, blank=True, default='')
    date = models.DateTimeField()
    link = models.URLField(blank=True, default='')
    attendees = models.ManyToManyField(User, through=Attendee, blank=True)

    def __str__(self):
        return '%s %s' % (self.event_type, self.anime.title)

    def get_date(self):
        locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
        return self.date.strftime('%A %-d %B %Y à %H h %M').lower()

    def to_html(self):
        common = '{type} le <strong>{date}</strong>'.format(
            type=self.get_event_type_display().capitalize(),
            date=self.get_date())
        if self.event_type == 'tv':
            return common + ' sur ' + self.channel

        if self.location:
            if self.link:
                link_tpl = ', <a href="{url}" target="_blank">{location}</a>'
                return common + link_tpl.format(
                    url=self.link, location=self.location)
            else:
                return common + ', ' + str(self.location)

        return common

    class Meta:
        ordering = ['date']


class Partner(models.Model):
    name = models.CharField(max_length=32)
    url = models.CharField(max_length=512)
    image = models.CharField(max_length=32, verbose_name="Fichier logo")

    class Meta:
        ordering = ['name'] 
