from django.contrib import admin
from irl.models import Location, Event


class EventAdmin(admin.ModelAdmin):
    list_display = ['anime', 'event_type', 'date', 'location', 'language']
    raw_id_fields = ['anime']


admin.site.register(Location)
admin.site.register(Event, EventAdmin)
