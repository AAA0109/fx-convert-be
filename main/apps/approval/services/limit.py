import logging
from decimal import Decimal
from dateutil import relativedelta
from datetime import date, datetime
from typing import Optional, Tuple, Union
from main.apps.account.models.company import Company
from main.apps.approval.models.limit import CompanyLimitSetting
from main.apps.currency.models.currency import Currency
from main.apps.oems.models import Ticket
from main.apps.marketdata.models.ref.instrument import InstrumentTypes
from main.apps.marketdata.services.initial_marketdata import Tenor, get_recent_data
from main.apps.oems.backend.calendar_utils import get_spot_dt
from main.apps.oems.backend.ccy_utils import determine_rate_side


logger = logging.getLogger(__name__)


class CompanyLimitService:
    company: Company
    discount: float = 2 / 100
    price_feed: str = 'OER'

    def __init__(self, company: Company) -> None:
        self.company = company

    def convert_to_company_currency(self, currency: Union[Currency, str], amount: float,
                                    value_date=Union[date, datetime]) -> Tuple[float, str, Optional[str]]:
        """
        Convert transaction amount to company's currency
        """
        currency = Currency.get_currency(currency=currency)

        rate = 1.0
        instrument_type = InstrumentTypes.SPOT
        side = None

        if currency != self.company.currency:
            fx_pair, side = determine_rate_side(
                currency, self.company.currency)
            market = fx_pair.market
            spot_dt, valid_days, spot_days = get_spot_dt(market)
            if isinstance(value_date, datetime):
                value_date = value_date.date()
            tenor = value_date
            if currency.mnemonic in ['RWF', 'SLL', 'XOF', 'ETB', 'ZMW', 'TZS']:
                tenor = Tenor.SPOT
            spot_rate, fwd_points, ws_feed = get_recent_data(fxpair=fx_pair, tenor=tenor,
                                                             price_feed=self.price_feed, spot_dt=spot_dt,
                                                             last=True)

            instrument_type = InstrumentTypes.SPOT if value_date <= spot_dt else InstrumentTypes.FORWARD
            rate = spot_rate['ask'] if side == Ticket.Sides.BUY else spot_rate['bid']

            if fx_pair.quote_currency == currency:
                rate = 1 / rate

        converted_amount = amount * rate
        return converted_amount, instrument_type, side

    def get_discounted_amount(self, amount: float) -> float:
        """
        Calculate amount after discount
        """
        return amount * (1 - self.discount)

    def is_amount_exceeding_limit(self, amount: float, instrument_type: str, side: str) -> bool:
        """
        Check if amount exceeding company transaction limit
        """
        try:
            company_limit = CompanyLimitSetting.objects.get(
                company=self.company)
        except CompanyLimitSetting.DoesNotExist:
            logger.info(
                f'No transaction limit setting for company {self.company.name}')
            company_limit = None

        if company_limit is None:
            return False

        if instrument_type == InstrumentTypes.SPOT:
            return amount > company_limit.max_amount_buy_spot if side == Ticket.Sides.BUY \
                else amount > company_limit.max_amount_sell_spot
        elif instrument_type == InstrumentTypes.FORWARD:
            return amount > company_limit.max_amount_buy_fwd if side == Ticket.Sides.BUY \
                else amount > company_limit.max_amount_sell_fwd

    def validate_transaction_limit(self, currency: Union[Currency, str], amount: Union[float, Decimal],
                                   value_date=Union[datetime, date]) -> Tuple[float, bool]:
        """
        Validate transaction amount based on company limit after the amount converted to company's currency
        """
        try:
            company_limit = CompanyLimitSetting.objects.get(
                company=self.company)
        except CompanyLimitSetting.DoesNotExist:
            logger.info(
                f'No transaction limit setting for company {self.company.name}')
            return amount, False

        currency = Currency.get_currency(currency=currency)
        if isinstance(amount, Decimal):
            amount = float(amount)
        if isinstance(value_date, datetime):
            value_date = value_date.date()

        converted_amount, instrument_type, side = self.convert_to_company_currency(currency=currency,
                                                                                   amount=amount,
                                                                                   value_date=value_date)
        discounted_amount = self.get_discounted_amount(amount=converted_amount)

        is_exceeding_limit = self.is_amount_exceeding_limit(amount=discounted_amount,
                                                            instrument_type=instrument_type, side=side)

        return discounted_amount, is_exceeding_limit

    def get_date_diff_in_month(self, date1:Union[date, datetime], date2:Union[date, datetime]) -> int:
        if isinstance(date1, datetime):
            date1 = date1.date()
        if isinstance(date2, datetime):
            date2 = date2.date()
        r = relativedelta.relativedelta(date1, date2)
        months_difference = (r.years * 12) + r.months
        return abs(months_difference)

    def is_tenor_exceeding_limit(self, value_date=Union[datetime, date]) -> Tuple[float, bool]:
        """
        Validate transaction tenor based on company tenor limit after we find the difference
        between payment value date and today date in months
        """
        try:
            company_limit = CompanyLimitSetting.objects.get(company=self.company)
        except CompanyLimitSetting.DoesNotExist:
            logger.info(f'No transaction limit setting for company {self.company.name}')
            return False

        if company_limit.max_tenor_in_month is not None:
            tenor_months = self.get_date_diff_in_month(date1=datetime.now().date(), date2=value_date)
            return tenor_months > company_limit.max_tenor_in_month
        return False
