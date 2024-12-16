from django.contrib import admin
from django.db.models import Value, F
from django.db.models.functions import Concat

from main.apps.country.admin import CountryAdmin
from main.apps.currency.models.proxy import Country

from .models import *


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('mnemonic', 'id', 'name', 'symbol', 'unit', 'numeric_code', 'country')


class FxPairAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'base_currency', 'quote_currency')
    list_filter = ('base_currency', 'quote_currency')
    search_fields = ['name']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            name=Concat(
                F("base_currency__mnemonic"),
                Value("/"),
                F("quote_currency__mnemonic")
            )
        )
        return qs


class StabilityIndexAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'year', 'currency', 'parent_index')

    def year(self, obj):
        return obj.date.strftime("%Y")


class DeliveryTimeAdmin(admin.ModelAdmin):
    list_display = (
        'currency',
        'currency_name',
        'country',
        'banking_open_utc',
        'banking_close_utc'
    )

    def currency(self, obj):
        try:
            return obj.currency.mnemonic
        except AttributeError:
            ...

    def currency_name(self, obj):
        try:
            return obj.currency.name.title()
        except AttributeError:
            ...

    @admin.display(description="Delivery SLA")
    def get_delivery_sla(self, obj):
        try:
            return "{} Bussiness Days".format(obj.delivery_sla)
        except AttributeError:
            ...


admin.site.register(Currency, CurrencyAdmin)
admin.site.register(FxPair, FxPairAdmin)
admin.site.register(StabilityIndex, StabilityIndexAdmin)
admin.site.register(Country, CountryAdmin)
