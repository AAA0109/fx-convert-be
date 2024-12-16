from daterangefilter.filters import DateRangeFilter
from django import forms
from django.contrib import admin, messages
from django.db.models import F
from django.db.models.functions import Concat
from django.urls import reverse
from django.utils.html import format_html
from django_admin_inline_paginator.admin import TabularInlinePaginated
from main.apps.cashflow.admin import CashFlowGeneratorAdmin, SingleCashFlowAdmin

from main.apps.core.utils.admin_search import MultiTermAndSearchMixin
from main.apps.oems.models import *
from main.apps.oems.models.proxy import CashflowGenerator, Cashflow, Payment
from main.apps.oems.services.life_cycle import LifeCycleEventUtils
from main.apps.oems.services.quote import QuoteUtil
from main.apps.payment.admin import PaymentAdmin


# ===============================
# Register your models here.
class CnyExecutionAdmin(MultiTermAndSearchMixin, admin.ModelAdmin):
    # autocomplete_fields = ['fxpair']
    list_select_related = (
        'fxpair__base_currency',
        'fxpair__quote_currency',
    )
    list_filter = (
        'company',
    )
    list_display = [field.name for field in CnyExecution._meta.get_fields()]
    search_fields = (
        'market_name',
        'company__name',
    )
    readonly_fields = ('company', 'fxpair',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            market_name=Concat(
                F("fxpair__base_currency__mnemonic"),
                F("fxpair__quote_currency__mnemonic")
            )
        )
        return qs


class CnyExecutionAdminInline(TabularInlinePaginated):
    model = CnyExecution
    extra = 0
    per_page = 20
    show_change_link = True
    autocomplete_fields = ('fxpair', )
    fields = (
        'active',
        'fxpair',
        'company',
        'spot_broker',
        'fwd_broker',
        'spot_rfq_type',
        'fwd_rfq_type',
    )
    readonly_fields = ('company',)


# ===============================

class WaitConditionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created',
        'modified',
        'rate_bid',
        'rate',
        'rate_ask',
        'expected_saving',
        'expected_saving_percentage',
        'lower_bound',
        'upper_bound',
        'regime',
        'start_time',
        'recommendation_time',
        'ai_model',
        'quote',
    )


@admin.action(description="Clean all company quote data")
def clean_company_quote_data(modeladmin, request, queryset):
    try:
        company = queryset[0].company
        QuoteUtil().clean_quote_data(company=company)
        messages.info(request,
                      f"Quote data cleaned successfully "
                      f"for {company.name}")
    except Exception as e:
        messages.error(request, str(e))


class OrderQuoteAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created',
        'modified',
        'company',
        'order_link',
        'pair',
        'user',
    )
    list_filter = (
        'company',
        'pair__base_currency',
        'pair__quote_currency'
    )
    actions = [clean_company_quote_data]

    def order_link(self, obj):
        try:
            url = reverse("admin:oems_order_change", args=[obj.order.id])
            return format_html('<a href="{}">Order ({})</a>', url, obj.order.id)
        except:
            return "-"


class ManualRequestAdmin(MultiTermAndSearchMixin, admin.ModelAdmin):
    list_display = [field.name for field in ManualRequest._meta.get_fields()]
    search_fields = (
        'ticket__company__name',
        'market_name',
        'side',
        'ticket__ticket_id',
    )
    list_filter = (
        ('created', DateRangeFilter),
    )


class TicketForm(forms.ModelForm):
    phase = forms.CharField()  # Override the status field to be a CharField

    class Meta:
        model = Ticket
        fields = '__all__'


def generate_revenue_report(modeladmin, request, queryset):
    from main.apps.oems.services.reporting import generate_report
    options = {
        'send': True,
        'show': True,
        'recips': [request.user.email],
    }
    generate_report(**options)


class TicketAdmin(MultiTermAndSearchMixin, admin.ModelAdmin):
    form = TicketForm
    actions = [generate_revenue_report]
    list_display = (
        'ticket_id',
        'market_name',
        'side',
        'action',
        'internal_state',
        'external_state',
        'phase',
        'external_quote',
        'spot_rate',
        'fwd_points',
        'quote_fee',
        'fee',
        'delivery_fee',
        'all_in_rate',
        'all_in_done',
        'all_in_cntr_done',
        'broker_id',
        'transaction_time',
        'execution_strategy',
        'trigger_time',
        'trader',
        'auth_user',
    )
    list_filter = (
        ('created', DateRangeFilter),
        'company',
        'action',
        'internal_state',
        'external_state',
        'phase',
        'market_name',
    )
    readonly_fields = ('ticket_id', 'market_name', 'side', 'action')
    search_fields = (
        'company__name',
        'market_name',
        'side',
        'ticket_id',
        'transaction_id',
        'cashflow_id',
        'transaction_group',
        'broker_id',
        'trader',
        'auth_user',
    )
    autocomplete_fields = (
        'fxpair',
    )


@admin.action(description="Clean all company life cycle event data")
def clean_company_life_cycle_event_data(modeladmin, request, queryset):
    try:
        company = queryset[0].company
        LifeCycleEventUtils().clean_life_cycle_event_data(company=company)
        messages.info(request,
                      f"Life cycle event data cleaned successfully "
                      f"for {company.name}")
    except Exception as e:
        messages.error(request, str(e))


class LifeCycleAdmin(MultiTermAndSearchMixin, admin.ModelAdmin):
    list_display = (
        'ticket_id',
        'company',
        'trader',
        'market_name',
        'side',
        'cashflow_id',
        'transaction_id',
        'transaction_group',
        'customer_id',
        'text',
    )
    list_filter = (
        ('created', DateRangeFilter),
        'company',
        'trader',
        'market_name',
    )
    search_fields = (
        'company__name',
        'market_name',
        'side',
        'ticket_id',
        'transaction_id',
        'cashflow_id',
        'transaction_group',
    )
    actions = [clean_company_life_cycle_event_data]


admin.site.register(Payment, PaymentAdmin)
admin.site.register(CashflowGenerator, CashFlowGeneratorAdmin)
admin.site.register(Cashflow, SingleCashFlowAdmin)
admin.site.register(WaitCondition, WaitConditionAdmin)
admin.site.register(Quote, OrderQuoteAdmin)
admin.site.register(ManualRequest, ManualRequestAdmin)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(LifeCycleEvent, LifeCycleAdmin)
