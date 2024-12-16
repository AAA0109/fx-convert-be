from django.contrib import admin
from .models import *


class CountryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'currency_code', 'use_in_average', 'use_in_explore',
                    'strictness_of_capital_controls', 'strictness_of_capital_controls_description')

