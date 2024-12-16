from django.contrib import admin

from main.apps.billing.models import Fee, Aum


# Register your models here.
class FeeAdmin(admin.ModelAdmin):
    list_display = ('amount','company', 'incurred', 'recorded', 'due', 'settled', 'fee_type', 'status')
    list_filter = ('company',)


class AumAdmin(admin.ModelAdmin):
    list_display = ('date', 'company', 'daily_aum', 'rolling_aum', 'rolling_window', 'actual_window', 'recorded')
    list_filter = ('company',)


admin.site.register(Fee, FeeAdmin)
admin.site.register(Aum, AumAdmin)
