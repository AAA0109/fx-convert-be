from django.contrib import admin
from .models import *


class FxSpotMarginAdmin(admin.ModelAdmin):
    list_display = ('id', 'broker', 'pair', 'date', 'rate', 'maintenance_rate', 'nfa_rate')


admin.site.register(FxSpotMargin, FxSpotMarginAdmin)
