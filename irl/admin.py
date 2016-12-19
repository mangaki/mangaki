from django.contrib import admin
from irl.models import Location, Event, Partner


class EventAdmin(admin.ModelAdmin):
    list_display = ['work', 'event_type', 'date', 'location', 'language']
    raw_id_fields = ['work']


class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'image']

admin.site.register(Location)
admin.site.register(Event, EventAdmin)
admin.site.register(Partner, PartnerAdmin)
