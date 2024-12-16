from django.contrib import admin

# Register your models here.
from django.contrib import admin
from rest_framework.authtoken.admin import TokenAdmin

from main.apps.webhook.models.proxy import Token
from .models.webhook import Event, EventGroup, Webhook


@admin.register(Event)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ('name', 'type')
    search_fields = ('name', 'type')


class WebhookEventInline(admin.TabularInline):
    model = EventGroup.events.through
    extra = 1


@admin.register(EventGroup)
class WebhookEventGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [WebhookEventInline]


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ('webhook_id', 'company', 'created_by', 'url', 'created')
    search_fields = ('company__name', 'created_by__username', 'url')
    list_filter = ('company',)
    filter_horizontal = ('events', 'groups')


admin.site.register(Token, TokenAdmin)
