from admin_extra_buttons.api import ExtraButtonsMixin, button, link
from django.contrib import admin
from django.db.models import Count
from django.shortcuts import resolve_url
from django_context_request import request

from main.apps.corpay.models import CorpaySettings, FXBalance, FXBalanceDetail, CurrencyDefinition, Forward, \
    ForwardQuote, ForwardGuidelines, TransactionCost, AumCost, SpotRate, UpdateRequest, ManualForwardRequest, Confirm, \
    FXBalanceAccount, SettlementAccount, Beneficiary, ApiRequestLog


class CorpaySettingsAdmin(admin.ModelAdmin):
    model = CorpaySettings
    list_display = (
        'company',
        'client_code',
        'user_code',
        'average_volume',
        'credit_facility',
        'max_horizon',
        'fee_wallet_id',
        'pangea_beneficiary_id',
    )
    list_filter = (
        'company',
    )
    fields = (
        'company',
        'client_code',
        'signature',
        'average_volume',
        'credit_facility',
        'max_horizon',
        'fee_wallet_id',
        'pangea_beneficiary_id',
        'user_code',
    )


class ManualForwardRequestInline(admin.StackedInline):
    model = ManualForwardRequest
    autocomplete_fields = ['pair']


class UpdateRequestAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    model = UpdateRequest
    inlines = [ManualForwardRequestInline]

    list_display = [
        'company',
        'created',
        'status',
    ]
    list_filter = (
        'status',
        'created',
        'company',
    )

    @link(href=None, change_form=True, change_list=False, permission='corpay.edit_view')
    def create_cash_flow(self, button):
        button.label = "Add/Edit Forward Position"

        error = ''
        if button.original.ndf_request.cashflow:
            error = 'Cashflow already exists'

        if error:
            button.href = f"javascript:window.alert('{error}')"
        else:
            back_url = request.path
            edit_url = resolve_url('corpay:forward_create', updaterequest_id=button.original.pk)
            button.href = f'{edit_url}?back_url={back_url}'""


class FXBalanceDetailInline(admin.TabularInline):
    model = FXBalanceDetail
    extra = 0
    fields = (
        'transaction_id',
        'order_number',
        'identifier',
        'name',
        'currency',
        'amount',
        'date'
    )


# Register your models here.
class FXBalanceAdmin(admin.ModelAdmin):
    model = FXBalance
    extra = 0
    show_change_link = True
    readonly_fields = ('id',)
    list_display = (
        'company',
        'account_number',
        'order_number',
        'amount',
        'debit_amount',
        'credit_amount',
        'is_posted',
        'currency',
        'balance'
    )
    list_filter = (
        'company',
        'currency'
    )
    fields = (
        'account_number',
        'order_number',
        'amount',
        'debit_amount',
        'credit_amount',
        'is_posted',
        'balance',
        'currency',
        'company'
    )
    inlines = [
        FXBalanceDetailInline
    ]


class CurrencyDefinitionAdmin(admin.ModelAdmin):
    model = CurrencyDefinition
    list_display = (
        'currency',
        'p10',
        'wallet',
        'wallet_api',
        'ndf',
        'fwd_delivery_buying',
        'fwd_delivery_selling',
        'outgoing_payments',
        'incoming_payments'
    )
    list_filter = (
        'currency',
        'p10',
        'wallet',
        'wallet_api',
        'ndf',
        'fwd_delivery_buying',
        'fwd_delivery_selling',
        'outgoing_payments',
        'incoming_payments'
    )


class ForwardInlineAdmin(admin.TabularInline):
    model = Forward
    extra = 0
    show_change_link = True


class ForwardAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'forward_quote',
        'corpay_forward_id',
        'order_number',
        'maturity_date',
        'drawdown_date',
        'drawdown_order_number',
        'origin_account',
        'destination_account',
        'destination_account_type',
        'funding_account',
        'cash_settle_account',
        'purpose_of_payment',
        'is_cash_settle'
    )

    list_filter = ('forward_quote__forward_guideline__credentials__company',)


class ForwardQuoteAdmin(admin.ModelAdmin):
    model = ForwardQuote
    inlines = [
        ForwardInlineAdmin
    ]
    list_display = (
        'quote_id',
        'rate_value',
        'rate_lockside',
        'rate_type',
        'rate_operation',
        'payment_currency',
        'payment_amount',
        'settlement_currency',
        'settlement_amount',
        'get_cashflow',
        'get_company'
    )

    list_filter = (
        'cashflow__account__company',
    )

    autocomplete_fields = (
        'rate_type',
    )

    @admin.display(description='Cashflow')
    def get_cashflow(self, obj):
        try:
            return obj.cashflow.name
        except AttributeError:
            ...

    @admin.display(description='Company')
    def get_company(sel, obj):
        try:
            return obj.cashflow.account.company.name
        except AttributeError:
            ...


class ForwardQuoteInlineAdmin(admin.TabularInline):
    model = ForwardQuote
    fields = (
        'quote_id',
        'rate_value',
        'rate_lockside',
        'rate_type',
        'rate_operation',
        'payment_currency',
        'payment_amount',
        'settlement_currency',
        'settlement_amount',
        'cashflow'
    )
    extra = 0
    show_change_link = True


class ForwardGuidelinesAdmin(admin.ModelAdmin):
    model = ForwardGuidelines
    inlines = [
        ForwardQuoteInlineAdmin
    ]
    list_display = (
        'id',
        'base_currency',
        'bookdate',
        'forward_maturity_days',
        'client_limit_amount',
        'client_limit_currency',
        'allow_book_deals',
        'forward_max_open_contract_interval',
        'margin_call_percent',
        'max_days',
        'hedging_agreement',
        'allow_book',
        'get_company'
    )

    list_filter = (
        'credentials__company',
    )

    @admin.display(description='Company')
    def get_company(sel, obj):
        try:
            return obj.credentials.company.name
        except AttributeError:
            ...


class TransactionCostAdmin(admin.ModelAdmin):
    model = TransactionCost
    list_display = (
        'currency_category',
        'average_volume_low',
        'average_volume_high',
        'notional_low',
        'notional_high',
        'cost_in_bps'
    )

    list_filter = (
        'currency_category',
    )


class AumCostAdmin(admin.ModelAdmin):
    model = AumCost
    list_display = (
        'currency_category',
        'average_volume_low',
        'average_volume_high',
        'annualized_rate',
        'minimum_rate'
    )

    list_filter = (
        'currency_category',
    )


class FXBalanceInlineAdmin(admin.TabularInline):
    model = SpotRate.fx_balances.through
    readonly_fields = ('fxbalance',)
    can_delete = False
    extra = 0

    def has_add_permission(self, request, obj):
        return False


class SpotRateAdmin(admin.ModelAdmin):
    model = SpotRate
    inlines = [
        FXBalanceInlineAdmin
    ]
    list_filter = (
        'company',
        'created',
    )
    list_display = (
        'pk',
        'fx_pair',
        'rate_value',
        'payment_amount',
        'user',
        'company',
        'order_number',
        'fx_balance_count',
        'created',
    )
    exclude = (
        'fx_balances',
    )
    search_fields = ['url']
    ordering = ['-pk']

    @admin.display(description='Fx balances')
    def fx_balance_count(self, obj):
        return obj.fx_balance_count or None

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(fx_balance_count=Count("fx_balances"))
        return queryset


@admin.register(Confirm)
class ConfirmAdmin(admin.ModelAdmin):
    list_display = (
        'company',
        'confirm_type',
        'deal_number',
        'order_number',
    )


@admin.register(ApiRequestLog)
class ApiRequestLogAdmin(admin.ModelAdmin):
    list_display = (
        'url',
        'method',
        'payload',
    )


class FXBalanceAccountAdmin(admin.ModelAdmin):
    list_display = (
        'company',
        'account',
        'currency',
        'ledger_balance',
        'balance_held',
        'available_balance',
        'account_number'
    )
    list_filter = (
        'company',
        'currency'
    )


class SettlementAccountAdmin(admin.ModelAdmin):
    list_display = (
        'settlement_account_id',
        'delivery_method',
        'company',
        'currency',
        'text',
        'payment_ident',
        'bank_name',
        'bank_account',
        'preferred',
        'selected',
        'category'
    )

    list_filter = (
        'company',
        'currency'
    )


class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = (
        'corpay_id',
        'client_integration_id',
        'company',
        'is_withdraw',
        'currency'
    )
    list_filter = (
        'company',
    )


class CorPayCredentialsInline(admin.TabularInline):
    model = CorpaySettings
    extra = 0
    show_change_link = True
    readonly_fields = ('id',)
    fields = (
        'client_code', 'signature', 'average_volume', 'credit_facility', 'fee_wallet_id', 'pangea_beneficiary_id',
        'user_code'
    )


class CorPayForwardQuoteInline(admin.TabularInline):
    model = ForwardQuote
    extra = 0
    show_change_link = True
    readonly_fields = ('id',)
    autocomplete_fields = ['rate_type']


admin.site.register(FXBalance, FXBalanceAdmin)
admin.site.register(CorpaySettings, CorpaySettingsAdmin)
admin.site.register(CurrencyDefinition, CurrencyDefinitionAdmin)
admin.site.register(ForwardQuote, ForwardQuoteAdmin)
admin.site.register(Forward, ForwardAdmin)
admin.site.register(SpotRate, SpotRateAdmin)
admin.site.register(FXBalanceAccount, FXBalanceAccountAdmin)
admin.site.register(SettlementAccount, SettlementAccountAdmin)
admin.site.register(Beneficiary, BeneficiaryAdmin)
