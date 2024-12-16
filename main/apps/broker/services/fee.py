from datetime import date
from typing import Optional, Tuple, Union

from django.db.models.query import QuerySet

from main.apps.account.models.company import Company
from main.apps.broker.models.broker import Broker
from main.apps.broker.models.fee import BrokerFeeCompany, CurrencyFee
from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.models.ref.instrument import InstrumentTypes
from main.apps.oems.models.cny import CnyExecution
from main.apps.oems.models.ticket import Ticket


class BrokerFeeProvider:
    company: Company

    def __init__(self, company: Company) -> None:
        self.company = company

    def __get_multiplier(self, side: Optional[str] = None) -> int:
        return -1 if side == "Sell" else 1

    def get_company_fee_object(self, fxpair: FxPair, tenor: str,
                               spot_dt: date) -> Optional[Union[BrokerFeeCompany, CurrencyFee]]:
        is_spot = True
        if isinstance(tenor, date):
            if tenor > spot_dt:
                is_spot = False
        elif tenor != 'spot':
            is_spot = False

        try:
            cny_execution = CnyExecution.objects.get(company=self.company,
                                                     fxpair=fxpair)
        except CnyExecution.DoesNotExist as e:
            try:
                cny_execution = CnyExecution.objects.get(company=self.company,
                                                     fxpair=FxPair.get_inverse_pair(pair=fxpair))
            except CnyExecution.DoesNotExist as e:
                return None

        if is_spot:
            broker = Broker.objects.get(
                broker_provider=cny_execution.spot_broker)
        else:
            broker = Broker.objects.get(
                broker_provider=cny_execution.fwd_broker)

        if is_spot:
            try:
                company_fee = BrokerFeeCompany.objects.get(
                    company=self.company,
                    broker=broker,
                    instrument_type=InstrumentTypes.SPOT,
                    sell_currency=fxpair.base_currency,
                    buy_currency=fxpair.quote_currency,
                )
            except BrokerFeeCompany.DoesNotExist as e:
                try:
                    company_fee = CurrencyFee.objects.get(
                        broker=broker,
                        instrument_type=InstrumentTypes.SPOT,
                        sell_currency=fxpair.base_currency,
                        buy_currency=fxpair.quote_currency,
                    )
                except CurrencyFee.DoesNotExist as e:
                    company_fee = None
        else:
            company_fee = BrokerFeeCompany.objects.filter(
                company=self.company,
                broker=broker,
                sell_currency=fxpair.base_currency,
                buy_currency=fxpair.quote_currency,
            ).exclude(instrument_type=InstrumentTypes.SPOT)\
                .order_by('-broker_fee')

            if len(company_fee) == 0:
                company_fee = CurrencyFee.objects.filter(
                    broker=broker,
                    sell_currency=fxpair.base_currency,
                    buy_currency=fxpair.quote_currency,
                ).exclude(instrument_type=InstrumentTypes.SPOT)\
                    .order_by('-broker_fee')

        if isinstance(company_fee, QuerySet):
            company_fee = list(company_fee)
            company_fee = company_fee[0] if len(company_fee) > 0 else None
        return company_fee

    def get_company_fee_object_from_ticket(self, ticket: Ticket) -> Optional[BrokerFeeCompany]:
        broker = Broker.objects.get(broker_provider=ticket.broker)
        instrument_type = ticket.instrument_type
        if instrument_type == Ticket.InstrumentTypes.FWD:
            instrument_type = InstrumentTypes.FORWARD

        try:
            company_fee = BrokerFeeCompany.objects.get(
                company=self.company,
                broker=broker,
                instrument_type=instrument_type,
                sell_currency=ticket.sell_currency,
                buy_currency=ticket.buy_currency,
            )
        except BrokerFeeCompany.DoesNotExist as e:
            try:
                company_fee = CurrencyFee.objects.get(
                    broker=broker,
                    instrument_type=instrument_type,
                    sell_currency=ticket.sell_currency,
                    buy_currency=ticket.buy_currency,
                )
            except CurrencyFee.DoesNotExist as e:
                company_fee = None
        return company_fee

    def get_broker_fee_from_ticket(self, ticket: Ticket) -> Tuple[float, float]:
        company_fee = self.get_company_fee_object_from_ticket(ticket=ticket)

        if company_fee is None:
            return 0.0, 0.0

        spot_rate = ticket.spot_rate
        if spot_rate is None:
            spot_rate = 0.0
        broker_fee = company_fee.broker_fee * spot_rate
        return round(broker_fee, 4), round(company_fee.broker_fee * 100, 2)

    def get_pangea_fee_from_ticket(self, ticket: Ticket) -> Tuple[float, float]:
        company_fee = self.get_company_fee_object_from_ticket(ticket=ticket)

        if company_fee is None:
            return 0.0, 0.0

        spot_rate = ticket.spot_rate
        if spot_rate is None:
            spot_rate = 0.0
        pangea_fee = company_fee.pangea_fee * spot_rate
        return round(pangea_fee, 4), round(company_fee.pangea_fee * 100, 2)

    def get_indicative_broker_fee(self, rate: float, fxpair: FxPair, tenor: str, spot_dt: date,
                                  side: str) -> Tuple[float, float]:
        company_fee = self.get_company_fee_object(fxpair=fxpair, tenor=tenor,
                                                  spot_dt=spot_dt)

        multiplier = self.__get_multiplier(side=side)
        if company_fee is None:
            return 0.0 * multiplier, 0.0 * multiplier

        broker_fee = company_fee.broker_fee * rate
        return round(broker_fee * multiplier, 4), round(company_fee.broker_fee * 100 * multiplier, 2)

    def get_indicative_pangea_fee(self, rate: float, fxpair: FxPair, tenor: str, spot_dt: date,
                                  side: str) -> Tuple[float, float]:
        company_fee = self.get_company_fee_object(fxpair=fxpair, tenor=tenor,
                                                  spot_dt=spot_dt)

        multiplier = self.__get_multiplier(side=side)
        if company_fee is None:
            return 0.0 * multiplier, 0.0 * multiplier

        pangea_fee = company_fee.pangea_fee * rate
        return round(pangea_fee * multiplier, 4), round(company_fee.pangea_fee * 100 * multiplier, 2)

    def get_wire_fee(self, fxpair: FxPair, tenor: str, spot_dt: date,
                     side: Optional[str] = None) -> float:
        company_fee = self.get_company_fee_object(fxpair=fxpair, tenor=tenor,
                                                  spot_dt=spot_dt)

        multiplier = self.__get_multiplier(side=side)
        if company_fee is None:
            return 0.0 * multiplier
        return round(company_fee.wire_fee * multiplier, 2)

    def to_fee_expression(self, fee: float, fee_pct: float) -> str:
        return f"{round(fee, 4)} / {round(fee_pct, 2)}%"
