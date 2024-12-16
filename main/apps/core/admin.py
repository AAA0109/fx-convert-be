import ast
import importlib
import json

from admin_extra_buttons.api import ExtraButtonsMixin, link
from admin_extra_buttons.api import button
from django.contrib import admin
from django.contrib import messages
from django.shortcuts import resolve_url
from django.utils.safestring import mark_safe
from django_celery_results.admin import TaskResultAdmin
from django_celery_results.models import TaskResult

from main.apps.core.models import Config, VendorOauth


class ConfigAdmin(admin.ModelAdmin):
    list_display = ('path', 'value')


@admin.register(VendorOauth)
class VendorServiceOauthAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    list_display = ('vendor', 'company', 'user')

    def has_add_permission(self, request):
        return False

    @link(href=None, change_form=False, change_list=True, permission='core.connect_oauth')
    def add_forward_position(self, button):
        button.label = "Connect Oauth Account"
        edit_url = resolve_url('core:connect-oauth')
        button.href = f'{edit_url}'""


def retry_celery_task_admin_action(modeladmin, request, queryset):
    msg = ''
    for task_res in queryset:
        if task_res.status != 'FAILURE':
            msg += f'{task_res.task_id} => Skipped. Not in "FAILURE" State<br>'
            continue
        try:
            task_actual_name = task_res.task_name.split('.')[-1]
            module_name = '.'.join(task_res.task_name.split('.')[:-1])
            kwargs = json.loads(task_res.task_kwargs)
            if isinstance(kwargs, str):
                kwargs = kwargs.replace("'", '"')
                kwargs = json.loads(kwargs)
                if kwargs:
                    getattr(importlib.import_module(module_name), task_actual_name).apply_async(kwargs=kwargs,
                                                                                                task_id=task_res.task_id)
            if not kwargs:
                args = ast.literal_eval(ast.literal_eval(task_res.task_args))
                getattr(importlib.import_module(module_name), task_actual_name).apply_async(args,
                                                                                            task_id=task_res.task_id)
            msg += f'{task_res.task_id} => Successfully sent to queue for retry.<br>'
        except Exception as ex:
            msg += f'{task_res.task_id} => Unable to process. Error: {ex}<br>'
    messages.error(request, mark_safe(msg))


retry_celery_task_admin_action.short_description = 'Retry Task'


class CustomTaskResultAdmin(TaskResultAdmin):
    actions = [retry_celery_task_admin_action, ]


admin.site.unregister(TaskResult)
admin.site.register(TaskResult, CustomTaskResultAdmin)
admin.site.register(Config, ConfigAdmin)

# ==============================================================================
# DJANGO ADMIN SITE SETTINGS
# ==============================================================================
admin.site.site_header = "Pangea - API"
admin.site.site_title = "Pangea"
admin.site.index_title = "Dashboard"

ADMIN_ORDERING = (
    ('account', (
        'Company',
        'User',
        'Beneficiary',
        'Wallet',
        'Payment'
    )),
    ('approval', (
        'CompanyLimitSetting',
        'CompanyApprovalSetting',
        'ApprovalLevelLimit',
        'GroupApprovalAuthorization',
        'CompanyApprovalBypass'
    )),
    ('oems', (
        'Payment',
        'CashflowGenerator',
        'Cashflow',
        'Quote',
        'Ticket',
        'LifeCycleEvent',
        'ManualRequest'
    )),
    ('settlement', (
        'Beneficiary',
        'BeneficiaryBroker',
        'Wallet',
        'BeneficiaryFieldConfig',
        'BeneficiaryValueMapping',
        'BeneficiaryFieldMapping',
        'BeneficiaryBrokerSyncResult'
    )),
    ('broker', (
        'BrokerInstrument',
        'BrokerCompany',
        'BrokerCompanyInstrument',
        'BrokerUserInstrument',
        'DeliveryTime',
        'CurrencyFee',
        'BrokerFeeCompany',
        'FeeTemplate',
        'ConfigurationTemplate',
        'BrokerAccountCapability',
        'CnyExecution',
        'BrokerTradingSession'
    )),
    ('post_office', (
        'Email',
        'Attachment',
        'EmailTemplate',
        'Log'
    )),
    ('auth_proxy', (
        'User',
        'UserActivity',
        'Group',
        'MFAMethod',
        'InvitationToken',
        'ResetPasswordToken'
    )),
    ('currency', (
        'Country',
        'Currency',
        'FxPair'
    )),
    ('marketdata', (
        'CmAsset',
        'CmSpot',
        'CorpayFxForward',
        'CorpayFxSpot',
        'FxEstimator',
        'FxForward',
        'FxMarketConvention',
        'FxOptionStrategy',
        'FxOption',
        'FxSpotCovariance',
        'FxSpotIntra',
        'FxSpotRange',
        'FxSpotVol',
        'FxSpot',
        'Instrument',
        'IrCurve',
        'IrDiscount',
        'OISRate',
        'TradingCalendarFincal',
        'TradingHolidaysCodeFincal',
        'TradingHolidaysFincal',
        'TradingHolidaysInfoFincal',
    )),
    ('dataprovider', (
        'DataProvider',
        'Source',
        'Profile',
        'Mapping',
        'CollectorConfig',
        'StorageConfig',
        'Value'
    )),
    ('django_celery_beat', (
        'ClockedSchedule',
        'CrontabSchedule',
        'IntervalSchedule',
        'PeriodicTask',
        'SolarSchedule'
    )),
    ('webhook', (
        'Token',
        'Event',
        'EventGroup',
        'Webhook',
    )),
    ('corpay', (
        'ApiRequestLog',
        'Beneficiary',
        'Confirm',
        'CorpaySettings',
        'CurrencyDefinition',
        'ForwardQuote',
        'Forward',
        'FXBalanceAccount',
        'FXBalance',
        'SettlementAccount',
        'SpotRate'
    )),
    ('reports', (
        'Metric',
        'Config',
        'VendorOauth',
        'GroupResult',
        'TaskResult',
        'LogEntry'
    )),
    ('django_celery_results', (
        'GroupResult',
        'TaskResult'
    )),
)

def get_app_list(self, request, app_label=None):
    app_dict = self._build_app_dict(request, app_label)

    if not app_dict:
        return

    NEW_ADMIN_ORDERING = []
    if app_label:
        for ao in ADMIN_ORDERING:
            if ao[0] == app_label:
                NEW_ADMIN_ORDERING.append(ao)
                break

    if not app_label:
        for app_key in list(app_dict.keys()):
            if not any(app_key in ao_app for ao_app in ADMIN_ORDERING):
                app_dict.pop(app_key)

    app_list = sorted(
        app_dict.values(),
        key=lambda x: [ao[0] for ao in ADMIN_ORDERING].index(x['app_label'])
    )

    for app, ao in zip(app_list, NEW_ADMIN_ORDERING or ADMIN_ORDERING):
        if app['app_label'] == ao[0]:
            for model in list(app['models']):
                if not model['object_name'] in ao[1]:
                    app['models'].remove(model)
                if app['app_label'] == 'post_office' and 'name' in model and\
                    model['name'] == 'Logs':
                    model['name'] = 'Activity History'
                if 'name' in model:
                    splits = model['name'].split(' ')
                    model['name'] = ' '.join([word.upper() if word in ['Ir', 'Fx', 'Cm', 'Ois', 'Mfa'] \
                                            else word.capitalize() for word in splits])
        try:
            app['models'].sort(key=lambda x: ao[1].index(x['object_name']))
        except:
            pass
    return app_list

admin.AdminSite.get_app_list = get_app_list
