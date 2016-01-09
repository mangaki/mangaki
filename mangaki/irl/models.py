from django.db import models
from mangaki.models import Anime
import locale


class Location(models.Model):
    title = models.CharField(max_length=64, verbose_name='Titre')
    address = models.TextField(verbose_name='Adresse')
    postal_code = models.CharField(max_length=5, verbose_name='Code postal')
    city = models.CharField(max_length=64, verbose_name='Ville')

    def __str__(self):
        return '%s, %s' % (self.title, self.city)


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

    def __str__(self):
        return '%s %s' % (self.event_type, self.anime.title)

    def get_date(self):
        locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
        return self.date.strftime('%A %-d %B %Y à %H h %M').lower()

    def to_html(self):
        date = self.get_date()
        if self.event_type == 'tv':
            return '%s <em>%s</em> le <strong>%s</strong> sur %s' % (self.get_event_type_display(), self.anime.title, date, self.channel)
        else:
            location = self.location
            if self.link:
                location = '<a href="%s" target="_blank">%s</a>' % (self.link, self.location)
            return '%s <em>%s</em> le <strong>%s</strong>, %s' % (self.get_event_type_display(), self.anime.title, date, location)

    class Meta:
        ordering = ['date']
