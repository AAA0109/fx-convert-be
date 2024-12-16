from admin_extra_buttons.api import ExtraButtonsMixin, button, link
from daterangefilter.filters import PastDateRangeFilter
from django.contrib import admin
from django.db.models import Q
from django.shortcuts import resolve_url
from django_context_request import request

from main.apps.account.models import Company, CashFlow
from main.apps.currency.models import FxPair
from main.apps.hedge.models import OMSOrderRequest, CompanyHedgeAction, FxPosition, AccountHedgeRequest, BenchmarkRate, \
    CurrencyMargin, InterestRate, CompanyFxPosition, CompanyEvent, AccountDesiredPositions, DraftFxForwardPosition, \
    ParachuteRecordAccount
from main.apps.hedge.models.fxforwardposition import FxForwardPosition


class OMSOrderRequestInline(admin.TabularInline):
    model = OMSOrderRequest
    extra = 0


class FxPositionInline(admin.TabularInline):
    model = FxPosition
    extra = 0


class AccountHedgeRequestInline(admin.TabularInline):
    model = AccountHedgeRequest
    extra = 0


class ParachuteRecordAccountInline(admin.TabularInline):
    model = ParachuteRecordAccount
    extra = 0


class CompanyHedgeActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'time')
    list_filter = (('time', PastDateRangeFilter),)
    inlines = [
        OMSOrderRequestInline,
        AccountHedgeRequestInline,
        ParachuteRecordAccountInline
    ]


class ParachuteRecordAccountAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_time',
        'bucket',
        'limit_value',
        'p_limit',
        'cashflows_npv',
        'forwards_pnl',
        'ann_volatility',
        'volatility',
        'p_no_breach',
        'time_horizon',
        'fraction_to_hedge',
        'sum_abs_remaining',
        'parachute_account',
        'realized_pnl',
        'unrealized_pnl',
        'adjusted_limit_value',
        'max_pnl',
        'account_pnl',
        'bucket_npv',
        'client_implied_cash_pnl',
        'forward_client_cash_one_day_pnl',
        'implied_minimum_client_cash'
    )
    list_filter = (
        ('company_hedge_action__time', PastDateRangeFilter),
        'parachute_account__company',
        'parachute_account',
        'bucket'
    )

    def get_time(self, obj):
        return obj.company_hedge_action.time
    get_time.short_description = "Time"
    get_time.admin_order_field = 'company_hedge_action__time'


class BenchmarkRateAdmin(admin.ModelAdmin):
    list_display = ('id', 'effective_date', 'broker', 'currency', 'rate')
    ordering = ('-effective_date', 'broker', 'currency')


class CurrencyMarginAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'broker', 'currency', 'tier_from', 'tier_to', 'rate', 'spread')
    ordering = ('-date', 'broker', 'currency', 'tier_from')


class InterestRateAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'broker', 'currency', 'tier_from', 'tier_to', 'rate', 'spread')
    ordering = ('-date', 'broker', 'currency', 'tier_from')


class CompanyFxPositionAdmin(admin.ModelAdmin):
    list_display = ('snapshot_event', 'company', 'broker_account', 'fxpair', 'amount', 'total_price')
    list_filter = ('company', 'broker_account', ('snapshot_event__time', PastDateRangeFilter))


class CompanyFxPositionInline(admin.TabularInline):
    model = CompanyFxPosition
    extra = 0


class CompanyEventAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'time', 'company', 'has_account_fx_snapshot', 'has_company_fx_snapshot', 'has_company_fx_snapshot',
        'has_hedge_action')
    list_filter = ('company', ('time', PastDateRangeFilter))
    inlines = [
        CompanyFxPositionInline,
        FxPositionInline
    ]


class AccountDesiredPositionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'amount', 'account', 'fxpair', 'company_hedge_action')
    list_filter = ('account', 'fxpair')


class FxForwardPositionInline(admin.TabularInline):
    model = FxForwardPosition
    autocomplete_fields = ('fxpair',)


class FxForwardPositionAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ('id', 'account', 'fxpair', 'amount', 'delivery_time', 'enter_time', 'forward_price',
                    'unwind_price', 'unwind_time')
    list_filter = (('enter_time', PastDateRangeFilter), 'cashflow__account__company', 'cashflow__account')
    autocomplete_fields = ['fxpair']

    @link(href=None, change_form=True, change_list=False, permission='corpay.edit_view')
    def add_forward_position(self, button):
        button.label = "Edit Forward Position"
        error = ''
        if not button.original.cashflow:
            error = 'No Cashflow'

        if error:
            button.href = f"javascript:window.alert('{error}')"
        else:
            back_url = request.path
            edit_url = resolve_url('corpay:forward_edit', pk=button.original.pk)
            button.href = f'{edit_url}?back_url={back_url}'""

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "fxpair":
            kwargs["queryset"] = FxPair.objects.order_by('base_currency__mnemonic', 'quote_currency__mnemonic')
        if db_field.name == 'cashflow':
            kwargs["queryset"] = CashFlow.objects.order_by('-pk')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class DraftFxForwardPositionCompanyFilter(admin.SimpleListFilter):
    title = 'Company'
    parameter_name = 'company'

    def lookups(self, request, model_admin):
        # Retrieve distinct companies from the model
        companies = Company.objects.values_list('id', 'name')
        return tuple((str(company[0]), company[1]) for company in companies)

    def queryset(self, request, queryset):
        # Apply the filter based on the selected company
        company_id = self.value()
        if company_id:
            return queryset.filter(
                Q(cashflow__account__company_id=company_id) | Q(draft_cashflow__company_id=company_id))
        return queryset


class DraftFxForwardPositionAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'cashflow', 'draft_cashflow', 'risk_reduction', 'is_cash_settle',
                    'estimated_fx_forward_price', 'company', 'purpose_of_payment', 'origin_account',
                    'destination_account', 'funding_account', 'cash_settle_account')
    list_filter = (DraftFxForwardPositionCompanyFilter, 'status')

    def get_company(self, obj):
        if obj.cashflow:
            return obj.cashflow.account.company
        if obj.draft_cashflow:
            return obj.draft_cashflow.company


class OMSOrderRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'company_hedge_action', 'broker_account', 'pair', 'unrounded_amount', 'requested_amount',
                    'filled_amount', 'total_price', 'commission', 'cntr_commission', 'status', 'expected_cost')
    list_filter = ('company_hedge_action__company',)


admin.site.register(CompanyHedgeAction, CompanyHedgeActionAdmin)
admin.site.register(BenchmarkRate, BenchmarkRateAdmin)
admin.site.register(CurrencyMargin, CurrencyMarginAdmin)
admin.site.register(InterestRate, InterestRateAdmin)
admin.site.register(CompanyFxPosition, CompanyFxPositionAdmin)
admin.site.register(CompanyEvent, CompanyEventAdmin)
admin.site.register(AccountDesiredPositions, AccountDesiredPositionsAdmin)
admin.site.register(FxForwardPosition, FxForwardPositionAdmin)
admin.site.register(DraftFxForwardPosition, DraftFxForwardPositionAdmin)
admin.site.register(OMSOrderRequest, OMSOrderRequestAdmin)
admin.site.register(ParachuteRecordAccount, ParachuteRecordAccountAdmin)
