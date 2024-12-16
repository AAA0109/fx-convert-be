from django.contrib import admin
from .models import sge

@admin.register(sge)
class SGEAdmin(admin.ModelAdmin):
    list_display = ['date', 'value_type', 'value', 'currency', 'country_codes']
    list_filter = ('currency', 'value_type')


