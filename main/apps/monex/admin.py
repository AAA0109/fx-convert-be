from django.contrib import admin

from main.apps.monex.models import MonexCompanySettings


# Register your models here.
class MonexCompanySettingsInline(admin.TabularInline):
    model = MonexCompanySettings
    extra = 0
    show_change_link = True
    readonly_fields = ('id',)
    fields = (
        'entity_id',
        'customer_id',
        'company_name'
    )
