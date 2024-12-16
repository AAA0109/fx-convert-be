from django.contrib import admin

from main.apps.approval.models.approval import (
    ApprovalLevelLimit,
    CompanyApprovalBypass,
    CompanyApprovalSetting,
    GroupApprovalAuthorization
)
from main.apps.approval.models.limit import CompanyLimitSetting


class CompanyLimitSettingInline(admin.TabularInline):
    model = CompanyLimitSetting
    extra = 0
    show_change_link = True
    readonly_fields = ('id',)
    fields = (
        'max_amount_sell_spot',
        'max_amount_buy_spot',
        'max_amount_sell_fwd',
        'max_amount_buy_fwd',
        'max_tenor_in_month'
    )


class CompanyApprovalSettingInline(admin.TabularInline):
    model = CompanyApprovalSetting
    extra = 0
    show_change_link = True
    readonly_fields = ('id',)
    fields = (
        'approval_method',
        'approval_trigger',
        'min_approval_trigger_amount',
        'enable_dual_approval'
    )


class ApprovalLevelLimitInline(admin.TabularInline):
    model = ApprovalLevelLimit
    extra = 0
    show_change_link = True
    readonly_fields = ('id',)
    fields = (
        'approval_level',
        'max_approval_amount'
    )


class GroupApprovalAuthorizationInline(admin.TabularInline):
    model = GroupApprovalAuthorization
    extra = 0
    show_change_link = True
    readonly_fields = ('id',)
    fields = (
        'group',
        'approval_level'
    )


class CompanyApprovalBypassInline(admin.TabularInline):
    model = CompanyApprovalBypass
    extra = 0
    show_change_link = True
    readonly_fields = ('id',)
    fields = (
        'user',
    )

# ======================= ADMIN VIEW =======================

class CompanyLimitSettingAdmin(admin.ModelAdmin):
    model = CompanyLimitSetting
    list_display = (
        'id',
        'company',
        'max_amount_sell_spot',
        'max_amount_buy_spot',
        'max_amount_sell_fwd',
        'max_amount_buy_fwd',
        'max_tenor_in_month'
    )
    list_filter = ('company',)


class CompanyApprovalSettingAdmin(admin.ModelAdmin):
    model = CompanyApprovalSetting
    list_display = (
        'id',
        'company',
        'approval_method',
        'approval_trigger',
        'min_approval_trigger_amount',
        'enable_dual_approval'
    )
    list_filter = ('company',)


class ApprovalLevelLimitAdmin(admin.ModelAdmin):
    model = ApprovalLevelLimit
    list_display = (
        'id',
        'company',
        'approval_level',
        'max_approval_amount'
    )
    list_filter = ('company',)


class GroupApprovalAuthorizationAdmin(admin.ModelAdmin):
    model = GroupApprovalAuthorization
    list_display = (
        'id',
        'company',
        'group',
        'approval_level'
    )
    list_filter = ('company',)


class CompanyApprovalBypassAdmin(admin.ModelAdmin):
    model = CompanyApprovalBypass
    list_display = (
        'id',
        'get_company',
        'user'
    )
    list_filter = ('user__company',)

    def get_company(self, obj:CompanyApprovalBypass):
        return obj.user.company if obj.user.company else ''

admin.site.register(CompanyLimitSetting, CompanyLimitSettingAdmin)
admin.site.register(CompanyApprovalSetting, CompanyApprovalSettingAdmin)
admin.site.register(ApprovalLevelLimit, ApprovalLevelLimitAdmin)
admin.site.register(GroupApprovalAuthorization, GroupApprovalAuthorizationAdmin)
admin.site.register(CompanyApprovalBypass, CompanyApprovalBypassAdmin)
