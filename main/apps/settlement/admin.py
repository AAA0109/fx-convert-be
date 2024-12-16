from typing import Any
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from main.apps.currency.models.currency import Currency

from .models import (
    Beneficiary,
    BeneficiaryFieldMapping, BeneficiaryFieldConfig, BeneficiaryValueMapping, BeneficiaryBroker,
    BeneficiaryBrokerSyncResult,
    Wallet, WalletBalance
)


class BeneficiaryResource(resources.ModelResource):
    destination_currency = fields.Field(
        column_name='destination_currency',
        attribute='destination_currency',
        widget=ForeignKeyWidget(Currency, field='mnemonic')
    )

    class Meta:
        model = Beneficiary


@admin.register(Beneficiary)
class BeneficiaryAdmin(ImportExportModelAdmin):
    resource_class = BeneficiaryResource
    list_display = (
        'beneficiary_id', 'company', 'beneficiary_alias', 'beneficiary_name', 'beneficiary_account_type',
        'classification', 'destination_country', 'destination_currency',
        'bank_account_number', 'bank_name', 'status'
    )
    search_fields = ('beneficiary_id', 'beneficiary_name',
                     'beneficiary_email', 'bank_account_number', 'bank_name')
    list_filter = ('company', 'destination_country',
                   'destination_currency', 'status')
    readonly_fields = ('beneficiary_id', 'created', 'modified')
    fieldsets = (
        (None, {
            'fields': (
                'beneficiary_id', 'external_id', 'company', 'status', 'reason'
            )
        }),
        ('Payment Information', {
            'fields': (
                'destination_country', 'destination_currency', 'payment_methods',
                'settlement_methods', 'preferred_method', 'payment_reference'
            )
        }),
        ('Beneficiary Information', {
            'fields': (
                'beneficiary_account_type', 'beneficiary_name', 'beneficiary_alias',
                'beneficiary_address_1', 'beneficiary_address_2', 'beneficiary_country',
                'beneficiary_region', 'beneficiary_postal', 'beneficiary_city',
                'beneficiary_phone', 'beneficiary_email', 'classification',
                'default_purpose', 'default_purpose_description'
            )
        }),
        ('Identification', {
            'fields': ('date_of_birth', 'identification_type', 'identification_value')
        }),
        ('Bank Information', {
            'fields': (
                'bank_account_type', 'bank_code', 'bank_account_number',
                'bank_account_number_type', 'bank_name', 'bank_country', 'bank_region',
                'bank_city', 'bank_postal', 'bank_address_1', 'bank_address_2',
                'bank_branch_name', 'bank_instruction', 'bank_routing_code_value_1',
                'bank_routing_code_type_1', 'bank_routing_code_value_2', 'bank_routing_code_type_2'
            )
        }),
        ('Inter-bank Information', {
            'fields': (
                'inter_bank_account_type', 'inter_bank_code', 'inter_bank_account_number',
                'inter_bank_account_number_type', 'inter_bank_name', 'inter_bank_country',
                'inter_bank_region', 'inter_bank_city', 'inter_bank_postal',
                'inter_bank_address_1', 'inter_bank_address_2', 'inter_bank_branch_name',
                'inter_bank_instruction', 'inter_bank_routing_code_value_1',
                'inter_bank_routing_code_type_1', 'inter_bank_routing_code_value_2',
                'inter_bank_routing_code_type_2'
            )
        }),
        ('Additional Fields', {
            'fields': ('client_legal_entity', 'proxy_type', 'proxy_value', 'further_name', 'further_account_number',
                       'additional_fields', 'regulatory')
        }),
    )


@admin.register(BeneficiaryBroker)
class BeneficiaryBrokerAdmin(admin.ModelAdmin):
    list_display = ('beneficiary', 'broker',
                    'broker_beneficiary_id', 'beneficiary_company')

    search_fields = (
        'beneficiary__beneficiary_id', 'beneficiary__beneficiary_name', 'broker__name', 'broker_beneficiary_id')
    list_filter = ('beneficiary__company', 'broker',)

    def beneficiary_name(self, obj):
        return obj.beneficiary.beneficiary_name

    beneficiary_name.short_description = 'Beneficiary Name'

    def beneficiary_id(self, obj):
        return obj.beneficiary.beneficiary_id

    beneficiary_id.short_description = 'Beneficiary ID'

    def broker_name(self, obj):
        return obj.broker.name

    broker_name.short_description = 'Broker Name'

    def beneficiary_company(self, obj):
        return obj.beneficiary.company

    beneficiary_company.short_description = 'Company'

    fieldsets = (
        (None, {
            'fields': ('beneficiary', 'broker', 'broker_beneficiary_id')
        }),
    )


@admin.register(BeneficiaryFieldMapping)
class BeneficiaryFieldMappingAdmin(admin.ModelAdmin):
    list_display = ('beneficiary_field', 'broker_field', 'get_brokers')
    search_fields = ('beneficiary_field', 'broker_field')
    filter_horizontal = ('brokers',)

    def get_brokers(self, obj):
        return ", ".join([broker.name for broker in obj.brokers.all()])

    get_brokers.short_description = 'Brokers'


@admin.register(BeneficiaryFieldConfig)
class BeneficiaryFieldConfigAdmin(admin.ModelAdmin):
    list_display = ('field_name', 'get_brokers', 'hidden', 'is_required')
    list_filter = ('brokers', 'hidden', 'is_required')
    search_fields = ('field_name', 'description')
    filter_horizontal = ('brokers',)

    def get_brokers(self, obj):
        return ", ".join([broker.name for broker in obj.brokers.all()])

    get_brokers.short_description = 'Brokers'


@admin.register(BeneficiaryValueMapping)
class BeneficiaryValueMappingAdmin(admin.ModelAdmin):
    list_display = ('field_mapping', 'internal_value', 'broker_value')
    list_filter = ('field_mapping__beneficiary_field',
                   'field_mapping__broker_field')
    search_fields = ('internal_value', 'broker_value')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('field_mapping')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        'wallet_id', 'is_default', 'name', 'broker_account_id', 'currency',
        'account_number','bank_name', 'type', 'account_type',
        'method', 'status', 'colored_available_balance', 'last_synced')
    list_filter = ('company', 'type', 'status', 'currency', 'broker')
    search_fields = ('name', 'broker_account_id',
                     'account_number', 'external_id', 'wallet_id')
    readonly_fields = ('wallet_id', 'external_id', 'created',
                       'modified', 'last_synced_at', 'current_balance_details')

    fieldsets = (
        (None, {
            'fields': ('wallet_id', 'name', 'broker_account_id', 'external_id', 'type', 'account_type', 'method',
                       'status')
        }),
        (_('Company and Broker'), {
            'fields': ('company', 'broker')
        }),
        (_('Account Details'), {
            'fields': ('currency', 'account_number', 'bank_name', 'description')
        }),
        (_('Balance'), {
            'fields': ('current_balance_details',)
        }),
        (_('Sync Information'), {
            'fields': ('last_synced_at',)
        }),
        (_('Flags'), {
            'fields': ('hidden',)
        }),
        (_('Set as default'), {
            'fields': ('default',)
        }),
        (_('Timestamps'), {
            'fields': ('created', 'modified'),
        }),
    )

    def is_default(self, obj:Wallet):
        return format_html("<span>✅</span>") if obj.default \
            else format_html("<span>⛔</span>")

    is_default.short_description = 'Default'

    def colored_available_balance(self, obj):
        latest_balance = WalletBalance.objects.filter(
            wallet=obj).order_by('-timestamp').first()
        if latest_balance:
            balance = latest_balance.available_balance
            color = 'green' if balance >= 0 else 'red'
            balance_str = f"{balance:.2f}"
            return format_html('<span style="color: {};">{} {}</span>', color, balance_str, obj.currency)
        return _("N/A")

    colored_available_balance.short_description = _('Available Balance')

    def current_balance_details(self, obj):
        latest_balance = WalletBalance.objects.filter(
            wallet=obj).order_by('-timestamp').first()
        if latest_balance:
            return format_html(
                '<strong>{}</strong> {:.2f}<br>'
                '<strong>{}</strong> {:.2f}<br>'
                '<strong>{}</strong> {:.2f}<br>'
                '<strong>{}</strong> {}',
                _('Ledger Balance:'), latest_balance.ledger_balance,
                _('Balance Held:'), latest_balance.balance_held,
                _('Available Balance:'), latest_balance.available_balance,
                _('Last Updated:'), latest_balance.timestamp.strftime(
                    "%Y-%m-%d %H:%M:%S")
            )
        return _("No balance information available")

    current_balance_details.short_description = _('Current Balance Details')

    def last_synced(self, obj):
        if obj.last_synced_at:
            return obj.last_synced_at.strftime("%Y-%m-%d %H:%M:%S")
        return _("Never")

    last_synced.short_description = _('Last Synced')

    actions = ['make_active', 'make_inactive']

    @admin.action(description=_("Mark selected wallets as active"))
    def make_active(self, request, queryset):
        updated = queryset.update(status=Wallet.WalletStatus.ACTIVE)
        self.message_user(request, _(
            "%(updated)d wallets were successfully marked as active.") % {'updated': updated})

    @admin.action(description=_("Mark selected wallets as inactive"))
    def make_inactive(self, request, queryset):
        updated = queryset.update(status=Wallet.WalletStatus.INACTIVE)
        self.message_user(request,
                          _("%(updated)d wallets were successfully marked as inactive.") % {'updated': updated})

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company', 'broker', 'currency')

    def save_model(self, request: Any, obj: Wallet, form: Any, change: Any) -> None:
        if change and obj.default:
            Wallet.objects.filter(company=obj.company).exclude(id=obj.pk).update(default=False)
        return super().save_model(request, obj, form, change)


@admin.register(BeneficiaryBrokerSyncResult)
class BeneficiaryBrokerSyncResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_beneficiary', 'get_broker',
                    'get_bene_broker_id', 'sync_errors')
    readonly_fields = ('sync_errors', 'last_sync')

    def get_beneficiary(self, obj: BeneficiaryBrokerSyncResult):
        return obj.beneficiary.beneficiary_name

    get_beneficiary.short_description = 'Beneficiary Name'
    get_beneficiary.admin_order_field = 'beneficiary__beneficiary_name'

    def get_broker(self, obj: BeneficiaryBrokerSyncResult):
        return obj.broker.name

    get_broker.short_description = 'Broker'
    get_broker.admin_order_field = 'broker__name'

    def get_bene_broker_id(self, obj: BeneficiaryBrokerSyncResult):
        try:
            bene_broker = BeneficiaryBroker.objects.get(
                beneficiary=obj.beneficiary, broker=obj.broker)
            return bene_broker.broker_beneficiary_id
        except Exception as e:
            return None

    get_bene_broker_id.short_description = 'Beneficiary ID'
