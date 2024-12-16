from django.contrib import admin

from main.apps.pricing.models import Feed, FeedInstrument


class FeedInstrumentInline(admin.TabularInline):
    model = FeedInstrument
    extra = 0


class FeedAdmin(admin.ModelAdmin):
    list_display = ('id', 'feed_name', 'channel_group', 'tick_type',
                    'indicative', 'feed_type','collector_name','user', 'company', 'tag', 'enabled')
    search_fields = ['feed_name', 'channel_group']
    list_filter = ('tick_type', 'indicative')
    raw_id_fields = ('user', 'company')
    inlines = [FeedInstrumentInline]
    list_editable = ('enabled',)
    readonly_fields = ('tag',)


class FeedInstrumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'instrument_type', 'symbol', 'feed')
    search_fields = ['symbol']
    list_filter = ('instrument_type',)
    raw_id_fields = ('feed',)


admin.site.register(Feed, FeedAdmin)
admin.site.register(FeedInstrument, FeedInstrumentAdmin)
