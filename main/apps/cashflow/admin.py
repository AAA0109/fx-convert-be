from django.contrib import admin

from main.apps.cashflow.models import SingleCashFlow, CashFlowGenerator


# Register your models here.
@admin.register(SingleCashFlow)
class SingleCashFlowAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cashflow_id",
        "company",
        "amount",
        "buy_currency",
        "sell_currency",
        "lock_side",
        "name",
        "pay_date",
        "created",
        "modified"
    )
    list_filter = (
        "company",
    )
    search_fields = (
        "cashflow_id",
    )


class SingleCashFlowInline(admin.TabularInline):
    model = SingleCashFlow
    extra = 0


@admin.register(CashFlowGenerator)
class CashFlowGeneratorAdmin(admin.ModelAdmin):
    inlines = [
        SingleCashFlowInline
    ]
    list_display = (
        'cashflow_id',
        'company',
        'amount',
        'buy_currency',
        'sell_currency',
        'lock_side',
    )
    list_filter = (
        'company',
    )
    search_fields = (
        'cashflow_id',
    )
