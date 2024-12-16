from django.contrib import admin, messages
from django.db.models import Prefetch
from django.template.loader import render_to_string
from django_admin_inline_paginator.admin import TabularInlinePaginated
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from main.apps.broker.models import ConfigurationTemplateBroker, ConfigurationTemplate
from main.apps.broker.models.broker import BrokerAccountCapability, Broker, BrokerAccount, BrokerCompany
from main.apps.broker.models.broker_instrument import BrokerInstrument
from main.apps.broker.models.trading_session import BrokerTradingSession
from main.apps.broker.models.company_perm import BrokerCompanyInstrument
from main.apps.broker.models.configuration import FeeTemplate
from main.apps.broker.models.fee import BrokerFeeCompany, CurrencyFee
from main.apps.broker.models.proxy import CnyExecution, DeliveryTime
from main.apps.broker.models.user_perm import BrokerUserInstrument
from main.apps.broker.services.broker_fee_updater import BrokerFeeUpdater
from main.apps.core.utils.admin_search import MultiTermAndSearchMixin
from main.apps.currency.admin import DeliveryTimeAdmin
from main.apps.currency.models import Currency
from main.apps.oems.admin import CnyExecutionAdmin


class BrokerAccountInline(admin.TabularInline):
    model = BrokerAccount
    extra = 0
    show_change_link = True
    readonly_fields = ('id',)
    fields = ('id', 'broker', 'broker_account_name', 'account_type', 'capabilities')


class BrokerAccountCapabilityAdmin(admin.ModelAdmin):
    list_display = ('id', 'type')


class BrokerAdmin(MultiTermAndSearchMixin, admin.ModelAdmin):
    inlines = [
        BrokerAccountInline
    ]
    list_display = ('id', 'name', 'execution_method', "broker_provider", "supported_instruments")
    search_fields = (
        'name',
    )


class BrokerInstrumentAdmin(MultiTermAndSearchMixin, admin.ModelAdmin):
    list_display = (
        'broker', 'instrument', 'base_ccy', 'counter_ccy', 'active', 'buy', 'sell', 'buy_wallet', 'sell_wallet',
        'buy_cost', 'buy_cost_unit', 'sell_cost', 'sell_cost_unit', 'buy_fee', 'buy_fee_unit', 'sell_fee',
        'sell_fee_unit',
        'delivery_sla', 'cutoff_time', 'funding_models', 'execution_types', 'api_types', 'wire_fee', 'wire_fee_unit',
        'custom',)
    search_fields = (
        'broker__name',
        'instrument__name',
        'base_ccy',
        'counter_ccy',
    )
    autocomplete_fields = (
        'instrument',
    )


class BrokerCompanyInstrumentAdmin(MultiTermAndSearchMixin, admin.ModelAdmin):
    list_display = (
        'broker_instrument', 'company', 'staging', 'active', 'default_exec_strat', 'default_hedge_strat',
        'default_algo',
        'use_triggers', 'rfq_type', 'min_order_size_buy', 'max_order_size_buy', 'min_order_size_sell',
        'max_order_size_sell', 'unit_order_size_buy', 'unit_order_size_sell', 'max_tenor_months')
    list_filter =  (
        'company',
    )
    search_fields = (
        'broker_instrument__broker__name',
        'broker_instrument__instrument__name',
        'company__name',
    )


class BrokerCompanyInstrumentAdminInline(MultiTermAndSearchMixin, TabularInlinePaginated):
    model = BrokerCompanyInstrument
    extra = 0
    per_page = 20
    show_change_link = True
    fields = (
        'broker_instrument',
        'staging',
        'active',
        'default_exec_strat',
        'default_hedge_strat',
        'default_algo',
        'use_triggers',
        'rfq_type',
        'min_order_size_buy',
        'max_order_size_buy',
        'min_order_size_sell',
        'max_order_size_sell',
        'unit_order_size_buy',
        'unit_order_size_sell',
        'max_tenor_months',
    )
    autocomplete_fields = ('broker_instrument',)
    search_fields = (
        'broker_instrument__broker__name',
        'broker_instrument__instrument__name',
        'company__name',
    )


# ===============

class BrokerUserInstrumentAdmin(MultiTermAndSearchMixin, admin.ModelAdmin):
    list_display = (
        'broker_instrument', 'company', 'role', 'staging', 'active', 'default_exec_strat',
        'default_hedge_strat',
        'default_algo', 'use_triggers', 'rfq_type', 'min_order_size_buy', 'max_order_size_buy', 'min_order_size_sell',
        'max_order_size_sell', 'unit_order_size_buy', 'unit_order_size_sell', 'max_tenor_months')
    autocomplete_fields = ('broker_instrument',)
    search_fields = (
        'broker_instrument__broker__name',
        'broker_instrument__instrument__name',
        'company__name'
    )


class BrokerUserInstrumentAdminInline(MultiTermAndSearchMixin, TabularInlinePaginated):
    model = BrokerUserInstrument
    extra = 0
    per_page = 25
    show_change_link = True
    list_diplay = (
        'active',
        'broker_instrument',
        'role',
        'staging',
        'default_exec_strat',
        'default_hedge_strat',
        'default_algo',
        'use_triggers',
        'rfq_type',
        'min_order_size_buy',
        'max_order_size_buy',
        'min_order_size_sell',
        'max_order_size_sell',
        'unit_order_size_buy',
        'unit_order_size_sell',
        'max_tenor_months',
    )
    autocomplete_fields = ('broker_instrument',)
    search_fields = (
        'broker_instrument__broker__name',
        'broker_instrument__instrument__name',
        'company__name'
    )


class CurrencyFeeResource(resources.ModelResource):
    broker = fields.Field(
        column_name='broker',
        attribute='broker',
        widget=ForeignKeyWidget(Broker, field='broker_provider'),
    )
    currency = fields.Field(
        column_name='buy_currency',
        attribute='buy_currency',
        widget=ForeignKeyWidget(Currency, field='mnemonic')
    )
    class Meta:
        model = CurrencyFee

@admin.action(description="Populate broker fee from fee template")
def populate_broker_fee_from_fee_template(modeladmin, request, queryset):
    try:
        fee_updater = BrokerFeeUpdater()
        fee_updater.update_broker_fee_data()
        messages.info(request, "Broker Fee successfully populated")
    except Exception as e:
        messages.error(request, str(e))

class CurrencyFeeAdmin(ImportExportModelAdmin):
    list_display = [field.name for field in CurrencyFee._meta.get_fields()]
    resource_class = CurrencyFeeResource
    list_filter = ('broker', 'instrument_type', 'sell_currency', 'buy_currency')
    actions = [populate_broker_fee_from_fee_template]


class BrokerCompanyAdmin(admin.ModelAdmin):
    list_display = ('company', 'broker', 'enabled')
    list_filter = ('broker', 'company')
    search_fields = ('broker', 'company__name')
    filter_horizontal = ('brokers',)
    ordering = ('company', 'broker')


class ConfigurationTemplateResource(resources.ModelResource):
    sell_currency = fields.Field(
        column_name='sell_currency',
        attribute='sell_currency',
        widget=ForeignKeyWidget(Currency, field='mnemonic')
    )
    buy_currency = fields.Field(
        column_name='buy_currency',
        attribute='buy_currency',
        widget=ForeignKeyWidget(Currency, field='mnemonic')
    )
    preferred_broker = fields.Field(
        column_name='preferred_broker',
        attribute='preferred_broker',
        widget=ForeignKeyWidget(Broker, field='broker_provider')
    )

    class Meta:
        model = ConfigurationTemplate


class ConfigurationTemplateBrokerInline(admin.TabularInline):
    model = ConfigurationTemplateBroker
    extra = 0


class ConfigurationTemplateAdmin(ImportExportModelAdmin):
    list_display = (
    'id', 'sell_currency', 'buy_currency', 'instrument_type', 'preferred_broker', 'display_broker_capabilities')
    list_filter = ('instrument_type', 'preferred_broker')
    search_fields = ('sell_currency__name', 'buy_currency__name', 'preferred_broker__name')
    inlines = [ConfigurationTemplateBrokerInline]
    resource_class = ConfigurationTemplateResource
    ordering = ('id',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related(
            Prefetch(
                'configurationtemplatebroker_set',
                queryset=ConfigurationTemplateBroker.objects.select_related('broker')
            )
        )

    def display_broker_capabilities(self, obj):
        brokers = obj.configurationtemplatebroker_set.all()
        broker_data = {ctb.broker.name: {
            'API': ctb.api,
            # Add more capabilities here, e.g.:
            # 'SomeOtherCapability': ctb.some_other_capability,
        } for ctb in brokers}
        capabilities = ['API']  # Add more capability names here as you add them
        context = {'broker_data': broker_data, 'capabilities': capabilities}
        return render_to_string('admin/broker/broker_capabilities_table.html', context)
    display_broker_capabilities.short_description = 'Broker Capabilities'


class FeeTemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'sell_currency', 'buy_currency', 'instrument_type', 'broker_markup')
    list_filter = ('instrument_type', 'sell_currency', 'buy_currency')
    search_fields = ('sell_currency__name', 'buy_currency__name', 'instrument_type')
    ordering = ('id',)


class BrokerFeeCompanyAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'company',
        'broker',
        'sell_currency',
        'buy_currency',
        'instrument_type',
        'broker_cost',
        'broker_fee',
        'pangea_fee',
        'rev_share',
        'wire_fee',
    )
    list_filter = ('company', 'broker', 'instrument_type')
    search_fields = ('company__name', 'broker__name', 'instrument_type')
    ordering = ('id',)


class BrokerFeeCompanyAdminInline(TabularInlinePaginated):
    model = BrokerFeeCompany
    extra = 0
    per_page = 20
    show_change_link = True
    fields = (
        'broker',
        'buy_currency',
        'sell_currency',
        'instrument_type',
        'broker_cost',
        'broker_fee',
        'pangea_fee',
        'rev_share',
        'wire_fee',
    )
    readonly_fields = ('company',)


class BrokerTradingSessionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'broker',
        'broker_country',
        'session_open_utc',
        'session_close_utc'
    )
    list_filter = ('broker',)
    search_fields = ('broker__broker_provider__name', 'broker_country')
    ordering = ('id',)


# Register your models here.
admin.site.register(Broker, BrokerAdmin)
admin.site.register(BrokerInstrument, BrokerInstrumentAdmin)
admin.site.register(BrokerCompanyInstrument, BrokerCompanyInstrumentAdmin)
admin.site.register(BrokerUserInstrument, BrokerUserInstrumentAdmin)
admin.site.register(BrokerAccountCapability, BrokerAccountCapabilityAdmin)
admin.site.register(CurrencyFee, CurrencyFeeAdmin)
admin.site.register(BrokerCompany, BrokerCompanyAdmin)
admin.site.register(ConfigurationTemplate, ConfigurationTemplateAdmin)
admin.site.register(FeeTemplate, FeeTemplateAdmin)
admin.site.register(BrokerFeeCompany, BrokerFeeCompanyAdmin)
admin.site.register(DeliveryTime, DeliveryTimeAdmin)
admin.site.register(CnyExecution, CnyExecutionAdmin)
admin.site.register(BrokerTradingSession, BrokerTradingSessionAdmin)
