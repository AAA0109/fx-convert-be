from django.contrib import admin

from main.apps.nium.models import NiumSettings


# Register your models here.
class NiumSettingsAdmin(admin.ModelAdmin):
    model = NiumSettings
    list_display = (
        'company',
        'customer_hash_id',
    )
    list_filter = ('company',)
    fields = (
        'company',
        'customer_hash_id',
    )


class NiumSettingsInline(admin.TabularInline):
    model = NiumSettings
    extra = 0
    show_change_link = True
    readonly_fields = ('id',)
    fields = (
        'company',
        'customer_hash_id',
    )
