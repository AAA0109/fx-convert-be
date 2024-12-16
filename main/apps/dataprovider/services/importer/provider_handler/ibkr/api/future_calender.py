import re
from datetime import datetime
from ib_insync import Contract, ContractDetails
import pytz
from typing import List, Sequence, Optional, Union

import pandas as pd

from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.base import IbkrApiHandler
from hdlib.DateTime.Date import Date
from main.apps.ibkr.models.future_contract import FutureContract
from main.apps.marketdata.models.future import FutureMarketData


class IbkrFutureCalendarHandler(IbkrApiHandler):

    model: FutureMarketData

    __datetime_format = '%Y%m%d%H%M'
    __tz = pytz.timezone('US/Eastern')

    def get_data_from_api(self) -> Optional[pd.DataFrame]:
        if self.client is None:
            return

        now = Date.now()
        date = now.astimezone(tz=self.__tz)

        future_contracts = FutureContract.get_active_contract(
            base=None, today=date)
        rows = []

        for future_contract in future_contracts:
            contract = self.__construct_request_contract_detail_parameters(
                future_contract=future_contract)
            if future_contract.symbol != None or future_contract.local_symbol != None:
                results = self.client.reqContractDetails(contract)
                if len(results) == 1:
                    hours_rows = self.__populate_row(
                        future_contract=future_contract, fetched_contract=results[0], date=date)
                    for hours_row in hours_rows:
                        rows.append(hours_row)

        self.df = pd.DataFrame(
            rows,
            columns=self.__get_dataframe_column()
        )
        return self.df

    def create_models_with_df(self) -> Sequence[FutureMarketData]:
        return [
            self.model(
                future_contract_id=row["future_contract_id"],
                date=row["date"],
                start_date=row["start_date"],
                end_date=row["end_date"],
                data_cut_id=row["DataCutId"],
                is_closed=row["is_closed"]
            )
            for index, row in self.df.iterrows() if row["future_contract_id"] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "start_date",
            "end_date",
            "future_contract_id"
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
            "future_contract_id",
            "date",
            "start_date",
            "end_date",
            "is_closed"
        ]

    def __populate_row(self, future_contract: FutureContract, fetched_contract: ContractDetails, date: datetime) -> List[Union[str, int, float]]:
        rows = []
        trading_hour_regex = r"(?P<start_date>[0-9]+):(?P<start_time>[0-9]+|CLOSED)-?(?P<end_date>[0-9]*)?:?(?P<end_time>[0-9]*)?"
        future_hours_data = fetched_contract.tradingHours if self.model.__name__ == "FutureTradingHours" else fetched_contract.liquidHours
        for trading_hours in future_hours_data.split(';'):
            result = re.search(trading_hour_regex, trading_hours)
            if result is None:
                continue
            start_date = result.group('start_date')
            start_time = result.group('start_time')
            end_date = result.group('end_date')
            end_time = result.group('end_time')
            is_closed = False
            if start_time == 'CLOSED':
                start_datetime = self.__tz.localize(datetime.strptime(
                    f'{start_date}0000', self.__datetime_format))
                start_datetime = Date.from_datetime(start_datetime)
                end_datetime = None
                is_closed = True
            else:
                start_datetime = self.__tz.localize(datetime.strptime(
                    f'{start_date}{start_time}', self.__datetime_format))
                end_datetime = self.__tz.localize(datetime.strptime(
                    f'{end_date}{end_time}', self.__datetime_format))

            rows.append([
                future_contract.id,
                date,
                start_datetime,
                end_datetime,
                is_closed
            ])
        return rows
