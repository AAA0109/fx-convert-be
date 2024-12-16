from django.contrib import admin

from main.apps.ibkr.models import WireInstruction, Application, SupportedFxPair
from main.apps.ibkr.models.fb import FundingRequest, FundingRequestStatus, FundingRequestProcessingStat, DepositResult, \
    WithdrawResult


# Register your models here.
class WireInstructionAdmin(admin.ModelAdmin):
    list_display = [field.name for field in WireInstruction._meta.get_fields()]


class ApplicationAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Application._meta.get_fields()]


class FundingRequestStatusInline(admin.TabularInline):
    model = FundingRequestStatus
    extra = 0


class FundingRequestProcessingStatInline(admin.TabularInline):
    model = FundingRequestProcessingStat
    extra = 0


class DepositResultInline(admin.TabularInline):
    model = DepositResult
    extra = 0


class WithdrawResultInline(admin.TabularInline):
    model = WithdrawResult
    extra = 0


class FundingRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'method', 'broker_account', 'request_submitted', 'response_data')
    inlines = [
        FundingRequestStatusInline,
        FundingRequestProcessingStatInline,
        DepositResultInline,
        WithdrawResultInline
    ]


class SupportedFxPairAdmin(admin.ModelAdmin):
    list_display = ('id', 'fxpair')
    list_filter = ('fxpair__base_currency', 'fxpair__quote_currency')


admin.site.register(WireInstruction, WireInstructionAdmin)
admin.site.register(Application, ApplicationAdmin)
admin.site.register(FundingRequest, FundingRequestAdmin)
admin.site.register(SupportedFxPair, SupportedFxPairAdmin)
