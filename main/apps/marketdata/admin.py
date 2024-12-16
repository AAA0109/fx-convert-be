from daterangefilter.filters import PastDateRangeFilter
from django.contrib import admin

from .models import FxEstimator, FxSpotVol, FxSpotCovariance, FxMarketConvention, CorpayFxSpot, \
    FxOption, FxOptionStrategy
from .models.cm import *
from .models.fincal.tradingcalendar import TradingCalendarFincal
from .models.fincal.tradingholidays import (
    TradingHolidaysCodeFincal,
    TradingHolidaysInfoFincal,
    TradingHolidaysFincal
)
from .models.fx.rate import (
    FxSpot,
    FxSpotRange,
    FxForward, CorpayFxForward, FxSpotIntra
)
from .models.ir.discount import (
    IrCurve, IrDiscount, OISRate
)
from .models.ref.instrument import Instrument


def get_spot_range_list():
    return (
        'id', 'date', 'pair', 'open', 'open_bid', 'open_ask', 'low', 'low_bid', 'low_ask', 'high', 'high_bid',
        'high_ask',
        'close', 'close_bid', 'close_ask'
    )


def get_spot_range_list_filter():
    return (
        ('date', PastDateRangeFilter),
        'pair__base_currency',
        'pair__quote_currency'
    )


def get_spot_list_display():
    return (
        'id', 'date', 'pair', 'rate', 'rate_bid', 'rate_ask', 'cut_type'
    )


def get_spot_list_filter():
    return (
        ('date', PastDateRangeFilter),
        'pair__base_currency',
        'pair__quote_currency'
    )


def get_spot_ordering():
    return ('date', 'pair')


class MarketdataAdminMixin:
    def cut_type(self, obj):
        if obj.data_cut is not None:
            return obj.data_cut.get_cut_type_display()

    autocomplete_fields = ['pair']


class FxSpotAdmin(MarketdataAdminMixin, admin.ModelAdmin):
    list_display = get_spot_list_display()
    list_filter = get_spot_list_filter()
    ordering = get_spot_ordering()


class CorpayFxSpotAdmin(MarketdataAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'date', 'rate', 'rate_bid', 'rate_ask', 'pair')
    list_filter = (
        ('date', PastDateRangeFilter),
        'pair__base_currency',
        'pair__quote_currency'
    )
    order = get_spot_ordering()


class FxSpotRangeAdmin(admin.ModelAdmin):
    list_display = get_spot_range_list()
    list_filter = get_spot_range_list_filter()
    ordering = get_spot_ordering()


class FxSpotVolAdmin(admin.ModelAdmin):
    list_display = ('date', 'vol', 'estimator', 'pair')
    list_filter = (
        ('date', PastDateRangeFilter),
        'pair__base_currency',
        'pair__quote_currency'
    )
    search_fields = ['pair__name']
    autocomplete_fields = ['pair']


class FxForwardAdmin(MarketdataAdminMixin, admin.ModelAdmin):
    list_display = (
        'id', 'date', 'tenor', 'pair', 'interest_days', 'delivery_days', 'expiry_days', 'rate', 'rate_bid', 'rate_ask',
        'fwd_points', 'fwd_points_bid', 'fwd_points_ask', 'depo_base', 'depo_quote', 'cut_type')
    list_filter = (
        ('date', PastDateRangeFilter),
        'pair__base_currency',
        'pair__quote_currency',
        'tenor'
    )
    ordering = ('date', 'pair', 'tenor')


class CorpayFxForwardAdmin(MarketdataAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'date', 'tenor', 'tenor_days', 'rate', 'rate_bid', 'rate_ask', 'fwd_points',
                    'fwd_points_bid', 'fwd_points_ask', 'data_cut', 'pair')
    list_filter = (
        ('date', PastDateRangeFilter),
        'tenor',
        'tenor_days',
        'pair__base_currency',
        'pair__quote_currency'
    )


class FxEstimatorAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'tag', 'parameters')
    ordering = ('id',)


class FxSpotCovarianceAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'covariance', 'estimator', 'pair_1', 'pair_2')
    list_filter = (
        ('date', PastDateRangeFilter),
        'pair_1__base_currency',
        'pair_1__quote_currency',
        'pair_2__base_currency',
        'pair_2__quote_currency',
    )
    search_fields = ['pair_1__name', 'pair_2__name']
    autocomplete_fields = ['pair_1', 'pair_2']


class IrCurveAdmin(admin.ModelAdmin):
    list_display = ('id', 'family', 'name', 'long_name', 'basis_convention', 'currency')
    ordering = ('id',)


class IrDiscountAdmin(MarketdataAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'date', 'maturity', 'maturity_days', 'discount', 'currency', 'curve', 'cut_type')
    list_filter = (('date', PastDateRangeFilter), 'currency', 'curve')
    ordering = ('date',)
    autocomplete_fields = []


class OISRateAdmin(MarketdataAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'date', 'tenor', 'maturity', 'maturity_days', 'rate', 'rate_bid', 'rate_ask', 'fixing_rate',
                    'spread', 'spread_index', 'currency', 'curve', 'cut_type')
    list_filter = (('date', PastDateRangeFilter), 'currency', 'curve')
    ordering = ('date',)
    autocomplete_fields = []


class CmSpotAdmin(MarketdataAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'date', 'mid_price', 'bid_price', 'ask_price', 'asset', 'cut_type')
    list_filter = (('date', PastDateRangeFilter), 'asset')
    ordering = ('date',)
    autocomplete_fields = []


class CmAssetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'currency', 'units')
    ordering = ('id',)


class FxMarketConventionAdmin(admin.ModelAdmin):
    list_display = ('id', 'min_lot_size', 'pair', 'is_supported')
    autocomplete_fields = ['pair']


class FincalTradingHolidaysCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'holiday')


class FincalTradingHolidaysInfoAdmin(admin.ModelAdmin):
    list_filter = ('currency',)
    list_display = ('code', 'center', 'country', 'currency', 'info_type', 'iso_country', 'define_1', 'define_2')


class FincalTradingHolidaysAdmin(admin.ModelAdmin):
    list_display = ('date', 'code', 'status')


class FincalTradingCalenderAdmin(admin.ModelAdmin):
    list_display = (
        'cen_code',
        'market',
        'irregular',
        'irreg_sess',
        'new_hours',
        'functions',
        'activity',
        'local_open',
        'local_close',
        'first_open',
        'last_open',
        'first_close',
        'last_close',
        'nyus_open',
        'nyus_close',
        'gmtt_open',
        'gmtt_close',
        'gmtoff_op',
        'fmtoff_cl'
    )
    search_fields = (
        'cen_code',
        'market'
    )


class InstrumentAdmin(admin.ModelAdmin):
    model = Instrument
    extra = 0
    show_change_link = True
    readonly_fields = ('id',)
    list_display = (
        'name', 'instrument_type', 'tradable_instrument', 'base_instrument', 'reference', 'symbology', 'multi_leg')
    list_filter = ('instrument_type', 'tradable_instrument', 'base_instrument', 'multi_leg')
    search_fields = (
        'name',
        'instrument_type'
    )


class FxOptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'pair', 'acquired_date', 'storage_type', 'file')
    list_filter = ('pair', 'acquired_date', 'storage_type')
    search_fields = ('pair__name',)


class FxOptionStrategyAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'pair', 'acquired_date', 'storage_type', 'file')
    list_filter = ('pair', 'acquired_date', 'storage_type')
    search_fields = ('pair__name',)


# Register your models here.
admin.site.register(FxSpot, FxSpotAdmin)
admin.site.register(FxSpotIntra, FxSpotAdmin)
admin.site.register(FxSpotRange, FxSpotRangeAdmin)
admin.site.register(FxSpotVol, FxSpotVolAdmin)
admin.site.register(IrCurve, IrCurveAdmin)
admin.site.register(IrDiscount, IrDiscountAdmin)
admin.site.register(OISRate, OISRateAdmin)

admin.site.register(CmAsset, CmAssetAdmin)
admin.site.register(CmSpot, CmSpotAdmin)
admin.site.register(FxForward, FxForwardAdmin)
admin.site.register(FxEstimator, FxEstimatorAdmin)
admin.site.register(FxSpotCovariance, FxSpotCovarianceAdmin)
admin.site.register(FxMarketConvention, FxMarketConventionAdmin)
admin.site.register(CorpayFxSpot, CorpayFxSpotAdmin)
admin.site.register(CorpayFxForward, CorpayFxForwardAdmin)
admin.site.register(TradingHolidaysCodeFincal, FincalTradingHolidaysCodeAdmin)
admin.site.register(TradingHolidaysInfoFincal, FincalTradingHolidaysInfoAdmin)
admin.site.register(TradingHolidaysFincal, FincalTradingHolidaysAdmin)
admin.site.register(TradingCalendarFincal, FincalTradingCalenderAdmin)
admin.site.register(Instrument, InstrumentAdmin)
admin.site.register(FxOption, FxOptionAdmin)
admin.site.register(FxOptionStrategy, FxOptionStrategyAdmin)
