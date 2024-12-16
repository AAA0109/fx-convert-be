from datetime import timedelta
import logging
from typing import List, Sequence, Optional, Union
import numpy as np
import pytz
import pandas as pd

from hdlib.DateTime.Date import Date
from main.apps.ibkr.models.future_contract import FutureContract
from main.apps.marketdata.models import FxSpotIntra
from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.base import IbkrApiHandler
from ib_insync import *

logger = logging.getLogger(__name__)

class IbkrFutureContarctApiHandler(IbkrApiHandler):
    model: FutureContract

    __last_dt_format = "%Y%m%d"
    __to_db_date_format = "%Y-%m-%d"

    def get_data_from_api(self) -> Optional[pd.DataFrame]:
        if self.client is None:
            return

        now = Date.now()
        tz = pytz.timezone('US/Eastern')
        date = now.astimezone(tz=tz)

        future_contracts = FutureContract.get_active_contract(
            base=None, today=date)
        rows = []
        columns = self.__get_dataframe_column()

        for future_contract in future_contracts:
            contract = self.__construct_request_contract_detail_parameters(
                future_contract=future_contract)
            if future_contract.symbol != None or future_contract.local_symbol != None:
                results = self.client.reqContractDetails(contract)
                if len(results) == 1:
                    rows.append(self.__populate_row(
                        future_contract=future_contract, fetched_contract=results[0]))

        rows = [row for row in rows if len(row) == len(columns)]

        self.df = pd.DataFrame(
            rows,
            columns=columns
        )
        return self.df

    def before_handle(self) -> pd.DataFrame:
        self.df = self.df.replace(r'^\s*$', np.nan, regex=True)
        self.df = self.df.replace({np.nan: None})
        return self.df

    def clean_data(self) -> pd.DataFrame:
        return self.df

    def add_data_cut_to_df(self):
        return

    def create_models_with_df(self) -> Sequence[FxSpotIntra]:
        return [
            self.model(
                base=row['base'],
                con_id=row['con_id'],
                currency=row['currency'],
                description=row['description'],
                exchange=row['exchange'],
                exchanges=row['exchanges'],
                fut_base=row['fut_base'],
                fut_cont_size=row['fut_cont_size'],
                fut_month=row['fut_month'],
                fut_month_symbol=row['fut_month_symbol'],
                fut_start_dt=row['fut_start_dt'],
                fut_symbol=row['fut_symbol'],
                fut_val_pt=row['fut_val_pt'],
                fut_year=row['fut_year'],
                last_dt=self.__change_date_format(row['last_dt']),
                lcode_long=row['lcode_long'],
                liquid_hours=row['liquid_hours'],
                local_symbol=row['local_symbol'],
                market_name=row['market_name'],
                min_tick=row['min_tick'],
                multiplier=row['multiplier'],
                price_magnifier=row['price_magnifier'],
                roll_dt=row['roll_dt'],
                sec_type=row['sec_type'],
                symbol=row['symbol'],
                timezone_id=row['timezone_id'],
                trading_hours=row['trading_hours']
            )
            for index, row in self.df.iterrows()
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "fut_symbol",
        ]

    def __construct_request_contract_detail_parameters(self, future_contract: FutureContract) -> Contract:
        contract = Contract()
        contract.symbol = future_contract.symbol or ""
        contract.localSymbol = future_contract.local_symbol or ""
        contract.multiplier = future_contract.multiplier or ""
        contract.secType = "FUT"
        contract.lastTradeDateOrContractMonth = str(
            future_contract.lcode_long) or ""
        contract.conId = future_contract.con_id or 0
        return contract

    def __get_dataframe_column(self) -> List[str]:
        return [
            "base",
            "con_id",
            "currency",
            "description",
            "exchange",
            "exchanges",
            "fut_base",
            "fut_cont_size",
            "fut_month_symbol",
            "fut_month",
            "fut_start_dt",
            "fut_symbol",
            "fut_val_pt",
            "fut_year",
            "last_dt",
            "lcode_long",
            "liquid_hours",
            "local_symbol",
            "market_name",
            "min_tick",
            "multiplier",
            "price_magnifier",
            "roll_dt",
            "sec_type",
            "symbol",
            "timezone_id",
            "trading_hours"
        ]

    def __populate_row(self, future_contract: FutureContract, fetched_contract: ContractDetails) -> List[Union[str, int, float]]:
        last_dt = Date.strptime(
            fetched_contract.contract.lastTradeDateOrContractMonth, self.__last_dt_format)

        if not fetched_contract.contract.conId:
            logger.warning(f"Intrument {future_contract.fut_symbol} is not populated properly because of an empty conId.")
            return []

        return [
            future_contract.base,
            fetched_contract.contract.conId,
            fetched_contract.contract.currency,
            fetched_contract.longName,
            fetched_contract.contract.primaryExchange,
            fetched_contract.validExchanges,
            future_contract.fut_base,
            future_contract.fut_cont_size,
            future_contract.fut_month_symbol,
            fetched_contract.contractMonth,
            self.__get_future_start_date(last_dt=last_dt),
            future_contract.fut_symbol,
            future_contract.fut_val_pt,
            future_contract.fut_year,
            fetched_contract.contract.lastTradeDateOrContractMonth,
            future_contract.lcode_long,
            fetched_contract.liquidHours,
            fetched_contract.contract.localSymbol,
            fetched_contract.marketName,
            fetched_contract.minTick,
            fetched_contract.contract.multiplier,
            fetched_contract.priceMagnifier,
            self.__get_roll_start_date(last_dt=last_dt),
            fetched_contract.contract.secType,
            future_contract.symbol,
            fetched_contract.timeZoneId,
            fetched_contract.tradingHours
        ]

    def __get_future_start_date(self, last_dt: Date, n_years_prior: Optional[int] = 1) -> str:
        fut_start_dt = self.__subtract_years(last_dt, n_years_prior)
        return fut_start_dt.strftime(self.__to_db_date_format)

    def __get_roll_start_date(self, last_dt: Date, n_days_prior: Optional[int] = 2) -> str:
        roll_start_dt = last_dt - timedelta(days=1)
        n_trading_days = 0
        while n_trading_days < n_days_prior:
            if roll_start_dt.weekday() not in [5, 6]:
                n_trading_days += 1
            if n_trading_days < n_days_prior:
                roll_start_dt = roll_start_dt - timedelta(days=1)
        return roll_start_dt.strftime(self.__to_db_date_format)

    def __subtract_years(self, dt: Date, years: int) -> Date:
        try:
            dt = dt.replace(year=dt.year-years)
        except ValueError:
            dt = dt.replace(year=dt.year-years, day=dt.day-1)
        return dt

    def __change_date_format(self, date_str: str) -> str:
        return Date.strptime(date_str, self.__last_dt_format).strftime(self.__to_db_date_format)
