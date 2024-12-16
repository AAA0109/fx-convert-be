from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from main.apps.account.models.company import Company
from main.apps.currency.models.currency import Currency
from main.apps.core.utils.admin_search import MultiTermAndSearchMixin

from main.apps.payment.models import *
# Register your models here.

class PaymentAdmin(MultiTermAndSearchMixin, admin.ModelAdmin):

    search_fields = (
        'company__name',
        'cashflow_generator__name',
        'purpose_of_payment',
        'cashflow_generator__sell_currency__mnemonic',
        'cashflow_generator__buy_currency__mnemonic',
    )

    list_display = (
        'id',
        'payment_id',
        'memo',
        'origin_account_id',
        'destination_account_id',
        'sell_currency',
        'buy_currency',
        'lock_side',
        'purpose_of_payment',
        'amount',
        'fee_in_bps',
        'company',
        'payment_status',
        'cashflow_generator_link',
    )

    list_filter = (
        'company',
    )

    def sell_currency(self, obj: Payment) -> Currency:
        return obj.cashflow_generator.sell_currency

    def buy_currency(self, obj: Payment) -> Currency:
        return obj.cashflow_generator.buy_currency

    def amount(self, obj: Payment) -> float:
        return obj.cashflow_generator.amount

    def lock_side(self, obj: Payment) -> str:
        return obj.cashflow_generator.lock_side

    def memo(self, obj: Payment) -> str:
        return obj.cashflow_generator.name

    def company(self, obj: Payment) -> Company:
        return obj.cashflow_generator.company

    def cashflow_generator_link(self, obj: Payment) -> str:
        try:
            url = reverse("admin:cashflow_cashflowgenerator_change", args=[obj.cashflow_generator.pk])
            return format_html('<a href="{}">Order ({})</a>', url, obj.cashflow_generator.name)
        except:
            return "-"
