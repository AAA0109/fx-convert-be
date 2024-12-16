from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_admin_inline_paginator.admin import TabularInlinePaginated

from main.apps.account.models import *
from main.apps.account.models.proxy import Beneficiary, Payment, Wallet
from main.apps.account.services.company import CompanyUtil
from main.apps.account.services.user import UserService
from main.apps.approval.admin import (
    ApprovalLevelLimitInline,
    CompanyApprovalBypassInline,
    CompanyApprovalSettingInline,
    CompanyLimitSettingInline,
    GroupApprovalAuthorizationInline
)
from main.apps.billing.models import FeeTier
from main.apps.broker.services.broker_fee_updater import CompanyBrokerFeeUpdater
from main.apps.hedge.models import HedgeSettings
from main.apps.notification.services.email_service import send_invoice_email
from main.apps.payment.admin import PaymentAdmin
from main.apps.settlement.admin import BeneficiaryAdmin, WalletAdmin
from main.apps.settlement.tasks import sync_beneficiary_from_brokers, sync_wallet_from_brokers
from .models.parachute_data import ParachuteData
from ..broker.admin import BrokerCompanyInstrumentAdminInline, BrokerFeeCompanyAdminInline
from ..broker.services.configuration import BrokerConfigurationService
from ..corpay.admin import CorPayCredentialsInline, CorPayForwardQuoteInline
from ..hedge.admin import FxForwardPositionInline
from ..history.admin import CompanySnapshotConfigurationInline
from ..history.services.snapshot_template import AccountSnapshotTemplateService
from ..monex.admin import MonexCompanySettingsInline
from ..nium.admin import NiumSettingsInline
from ..oems.admin import CnyExecutionAdminInline


class FeeTierInline(TabularInlinePaginated):
    model = FeeTier
    extra = 0
    per_page = 20


class CashFlowInline(TabularInlinePaginated):
    model = CashFlow
    extra = 0
    per_page = 20


class HedgeSettingsInline(TabularInlinePaginated):
    model = HedgeSettings
    per_page = 20


class ParachuteDataInline(TabularInlinePaginated):
    model = ParachuteData
    extra = 0
    per_page = 20
    show_change_link = True
    readonly_fields = ('id',)


class AccountAdmin(admin.ModelAdmin):
    change_form_template = 'admin/account/change_form.html'
    list_display = ('id', 'company', 'name', 'type', 'is_active')
    list_filter = ('company', 'type', 'is_active')
    inlines = [
        HedgeSettingsInline,
        CashFlowInline,
        ParachuteDataInline
    ]

    def response_change(self, request, obj):
        if "_create_snapshot_template" in request.POST:
            AccountSnapshotTemplateService.create_template_from_account(obj)
        return super().response_change(request, obj)


class AccountInline(TabularInlinePaginated):
    model = Account
    extra = 0
    per_page = 20
    show_change_link = True


class CashFlowNoteInline(TabularInlinePaginated):
    model = CashFlowNote
    extra = 0
    per_page = 20
    show_change_link = False
    readonly_fields = ('id', 'created', 'created_by', 'modified', 'modified_by', 'description',)


class CashflowAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ['admin/css/account.css']
        }

    inlines = [
        CashFlowNoteInline,
        CorPayForwardQuoteInline,
        FxForwardPositionInline
    ]
    model = CashFlow
    list_display = ('id', 'name', 'currency', 'amount', 'company', 'account', 'status', 'created', 'date', 'end_date',
                    'last_generated_point')
    list_filter = ('account__company', 'account', 'date')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "currency":
            kwargs["queryset"] = Currency.objects.order_by('mnemonic')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def company(self, obj):
        return obj.account.company


class DraftCashflowAdmin(admin.ModelAdmin):
    model = DraftCashFlow
    list_display = ('id', 'date', 'amount', 'name', 'end_date', 'company', 'account', 'action')
    list_filter = ('company', 'account', 'action')


@admin.action(description="Send company invoice email")
def send_invoice(modeladmin, request, queryset):
    for company in queryset.all():
        send_invoice_email(company=company)


class UserInline(TabularInlinePaginated):
    model = User
    extra = 0
    per_page = 20
    show_change_link = True
    can_delete = False
    readonly_fields = ('first_name', 'last_name', 'email', 'login')
    fields = ('first_name', 'last_name', 'email', 'login')

    def login(self, obj):
        url = UserService.generate_token_url(obj)
        return format_html(f'<a href="{url}">login</a>')


@admin.action(description="Populate company with default broker configurations")
def populate_broker_configuration(modeladmin, request, queryset):
    total_results = {
        'cny_executions_created': 0,
        'cny_executions_updated': 0,
        'broker_company_instruments_created': 0,
        'broker_company_instruments_updated': 0
    }
    for company in queryset:
        results = BrokerConfigurationService.populate_for_company(company)
        if results['success']:
            messages.success(request, results['message'])
        else:
            messages.error(request, results['message'])
        for key in total_results.keys():
            total_results[key] += results[key]
    messages.info(request,
                  f"Total CnyExecutions created: {total_results['cny_executions_created']}, "
                  f"updated: {total_results['cny_executions_updated']}")
    messages.info(request,
                  f"Total BrokerCompanyInstruments created:"
                  f" {total_results['broker_company_instruments_created']}, "
                  f"updated: {total_results['broker_company_instruments_updated']}")


@admin.action(description="Populate company's broker fee")
def populate_broker_fee_company(modeladmin, request, queryset):
    error = []
    success = []
    for company in queryset:
        try:
            company_fee_updater = CompanyBrokerFeeUpdater(company=company)
            company_fee_updater.populate_broker_fee()
            success.append(company.name)
        except Exception as e:
            logger.error(e)
            error.append(company.name)
    if len(success) > 0:
        messages.success(request,
                         f"Success populating broker fee for companies: "
                         f"{', '.join(success)}")
    if len(error) > 0:
        messages.error(request,
                         f"Error populating broker fee for companies: "
                         f"{', '.join(error)}")

@admin.action(description="Clean company data and delete company")
def clean_company_data_and_delete_company(modeladmin, request, queryset):
    error = []
    success = []
    for company in queryset:
        company_name = company.name
        try:
            CompanyUtil().clean_company_data_and_delete_company(company=company)
            success.append(company_name)
        except Exception as e:
            logger.error(e, exc_info=True)
            error.append(company_name)

    if len(success) > 0:
        messages.success(request,
                         f"Success clean and delete companies: "
                         f"{', '.join(success)}")
    if len(error) > 0:
        messages.error(request,
                         f"Error clean and delete companies: "
                         f"{', '.join(error)}")

@admin.action(description="Sync companies wallets from brokers")
def sync_companies_wallets_from_brokers(modeladmin, request, queryset):
    company_names = []
    for company in queryset:
        sync_wallet_from_brokers.delay(company_id=company.pk)
        company_names.append(company.name)
    messages.info(request,
                  f"Syncing {', '.join(company_names)} wallets from brokers in the background")

@admin.action(description="Sync companies beneficiaries from brokers")
def sync_companies_beneficiaries_from_brokers(modeladmin, request, queryset):
    company_names = []
    for company in queryset:
        sync_beneficiary_from_brokers.delay(company_id=company.pk)
        company_names.append(company.name)
    messages.info(request,
                  f"Syncing {', '.join(company_names)} beneficiaries from brokers in the background")


class CompanyAdmin(admin.ModelAdmin):
    change_form_template = "admin/company/change_form.html"
    list_display = ('id', 'name')
    list_display_links = ('name',)
    exclude = ('timezone', 'stripe_customer_id', 'stripe_setup_intent_id',
               'hs_company_id', 'service_interested_in', 'estimated_aum',
               'show_pnl_graph')
    inlines = [
        CorPayCredentialsInline,
        NiumSettingsInline,
        MonexCompanySettingsInline,
        CompanyLimitSettingInline,
        CompanyApprovalSettingInline,
        ApprovalLevelLimitInline,
        GroupApprovalAuthorizationInline,
        CompanyApprovalBypassInline,
        UserInline,
        CompanySnapshotConfigurationInline,
        CnyExecutionAdminInline,
        BrokerCompanyInstrumentAdminInline,
        BrokerFeeCompanyAdminInline,
    ]
    actions = [
        clean_company_data_and_delete_company,
        send_invoice,
        populate_broker_configuration,
        populate_broker_fee_company,
        sync_companies_wallets_from_brokers,
        sync_companies_beneficiaries_from_brokers,
    ]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'recipients':
            object_id = request.resolver_match.kwargs.get('object_id')
            kwargs['queryset'] = User.objects.filter(company_id=object_id)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def response_change(self, request, obj):
        if "_restore_snapshot_template" in request.POST:
            AccountSnapshotTemplateService.restore_template_for_company(obj)
        return super().response_change(request, obj)


class ParachuteCashflowAdmin(admin.ModelAdmin):
    model = ParachuteCashFlow
    list_display = (
        'id',
        'pay_date',
        'amount',
        'generation_time',
        'deactivation_date',
        'deactivated_by_rolloff',
        'initial_npv',
        'initial_spot',
        'final_npv',
        'final_spot',
        'account',
        'cashflow_generator',
        'currency',
        'created',
        'modified'
    )
    readonly_fields = ('id', 'created', 'modified')
    list_filter = ('account',)


@admin.register(User)
class UserAdmin(UserAdmin):
    """Define admin model for custom User model with no email field."""

    def login(self, obj):
        url = UserService.generate_token_url(obj)
        return format_html(f'<a href="{url}">login</a>')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone', 'timezone')}),
        (_('Third Party info'), {'fields': ('hs_contact_id',)}),
        (_('Permissions'), {'fields': ('is_active', 'phone_confirmed', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Account info'), {'fields': ('company',)})
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('id', 'email', 'company', 'first_name', 'last_name', 'is_staff', 'login')
    list_filter = ('company', 'groups', 'is_active', 'is_staff', 'is_superuser',)
    list_display_links = ('id', 'email')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)


admin.site.register(Account, AccountAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(Beneficiary, BeneficiaryAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(Payment, PaymentAdmin)
