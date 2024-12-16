from django.contrib import admin
from django_celery_results.admin import GroupResultAdmin
from auditlog.admin import LogEntryAdmin

from main.apps.core.admin import ConfigAdmin, CustomTaskResultAdmin, VendorServiceOauthAdmin
from main.apps.reports.models import *
from main.apps.reports.models.proxy import (
    Config,
    LogEntry,
    GroupResult,
    TaskResult,
    VendorOauth
)


class MetricAdmin(admin.ModelAdmin):
    list_display = (
        'ai_model',
        'start_date',
        'end_date',
        'avg_buy',
        'avg_sell',
        'avg_buy_saved',
        'avg_sell_gained',
        'avg_saved',
        'min_buy_saved',
        'min_sell_gained',
        'avg_execution_spread',
        'avg_start_spread',
        'spread_benefit',
        'max_execution_spread',
        'avg_wait',
        'min_wait',
        'max_wait'
    )
    search_fields = ['ai_model__name', 'start_date', 'end_date']
    list_filter = ('start_date', 'end_date')
    ordering = ('-start_date', '-end_date')


admin.site.register(Metric, MetricAdmin)
admin.site.register(Config, ConfigAdmin)
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(VendorOauth, VendorServiceOauthAdmin)

# TODO: Resolve error during editing following admin view
# So I temporary add celery result app menu
# admin.site.register(GroupResult, GroupResultAdmin)
# admin.site.register(TaskResult, CustomTaskResultAdmin)
