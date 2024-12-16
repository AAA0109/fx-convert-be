from daterangefilter.filters import PastDateRangeFilter
from django.contrib import admin

from main.apps.history.models import (
    AccountSnapshot,
    CompanySnapshot,
    ReconciliationRecord,
    UserActivity, AccountSnapshotTemplateData, CompanySnapshotConfiguration
)


class AccountSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'account', 'snapshot_time', 'last_snapshot', 'next_snapshot', 'change_in_realized_pnl_fxspot',
        'total_realized_pnl',
        'change_in_realized_pnl_fxforward',
        'unrealized_pnl_fxspot',
        'unrealized_pnl_fxforward',
        'directional_positions_value', 'cashflow_npv', 'change_in_npv', 'cashflow_fwd',
        'cashflow_abs_fwd', 'cashflow_roll_off', 'cashflow_roll_on', 'num_cashflows_rolled_off',
        'num_cashflows_rolled_on', 'num_cashflows_in_window', 'total_cashflow_roll_off', 'daily_commission',
        'cumulative_commission', 'daily_roll_value', 'cumulative_roll_value', 'daily_trading',
        'daily_unhedged_variance', 'daily_hedged_variance', 'unhedged_value', 'hedged_value', 'margin'
    )
    list_filter = (('snapshot_time', PastDateRangeFilter), 'account__company', 'account')


class AccountSnapshotTemplateDataAdmin(admin.ModelAdmin):
    list_filter = ('template_uuid',)
    def get_list_display(self, request):
        return list(field.name for field in self.model._meta.fields)


class CompanySnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'snapshot_time', 'company', 'total_cash_holding', 'total_cash_holding', 'excess_liquidity',
        'total_maintenance_margin', 'total_asset_value', 'live_cashflow_abs_fwd', 'demo_cashflow_abs_fwd',
        'num_live_cashflows_in_windows', 'num_demo_cashflows_in_windows', 'daily_roll_value', 'live_position_value',
        'demo_position_value', 'demo_unrealized_pnl', 'live_unrealized_pnl', 'live_change_in_realized_pnl',
        'demo_change_in_realized_pnl', 'live_total_realized_pnl', 'demo_total_realized_pnl'
    )
    list_filter = (('snapshot_time', PastDateRangeFilter), 'company')


class ReconciliationRecordAdmin(admin.ModelAdmin):
    list_display = [field.name for field in ReconciliationRecord._meta.get_fields()]
    list_filter = (('reference_time', PastDateRangeFilter), 'company')


class UserActivityAdmin(admin.ModelAdmin):
    list_display = [field.name for field in UserActivity._meta.get_fields()]


class CompanySnapshotConfigurationInline(admin.TabularInline):
    model = CompanySnapshotConfiguration
    extra = 0


# Register your models here.
admin.site.register(AccountSnapshot, AccountSnapshotAdmin)
admin.site.register(CompanySnapshot, CompanySnapshotAdmin)
admin.site.register(ReconciliationRecord, ReconciliationRecordAdmin)
admin.site.register(UserActivity, UserActivityAdmin)
admin.site.register(AccountSnapshotTemplateData, AccountSnapshotTemplateDataAdmin)
