from django.contrib import admin
from irl.models import Partner


class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'image']


admin.site.register(Partner, PartnerAdmin)
