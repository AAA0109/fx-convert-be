import re
from datetime import datetime
import pytz
from typing import Sequence, Optional

import pandas as pd

from main.apps.marketdata.models import TradingCalendar
from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.base import IbkrApiHandler
from hdlib.DateTime.Date import Date


class IbkrTradingCalendarHandler(IbkrApiHandler):
    model: TradingCalendar

    def get_data_from_api(self) -> Optional[pd.DataFrame]:
        if self.client is None:
            return
        now = Date.now()
        tz = pytz.timezone('US/Eastern')
        date = Date(now.year, now.month, now.day, 17, 0, 0)
        date = tz.localize(date)
        contracts = []
        trading_class_mapping = {}
        for fx_pair in self.get_supported_pairs():
            pair = fx_pair.base_currency.mnemonic + fx_pair.quote_currency.mnemonic
            contract = self.api.get_contract(type="forex", symbol=pair)
            contracts.append(contract)
            trading_class_mapping[f"{contract.symbol}{contract.currency}"] = fx_pair.id
        contracts = self.client.qualifyContracts(*contracts)
        rows = []
        for contract in contracts:
            details = self.client.reqContractDetails(contract)
            trading_hour_regex = r"(?P<start_date>[0-9]+):(?P<start_time>[0-9]+|CLOSED)-?(?P<end_date>[0-9]*)?:?(?P<end_time>[0-9]*)?"
            datetime_format = '%Y%m%d%H%M'
            tz = pytz.timezone(details[0].timeZoneId)
            for trading_hours in details[0].tradingHours.split(';'):
                result = re.search(trading_hour_regex, trading_hours)
                if result is None:
                    continue
                start_date = result.group('start_date')
                start_time = result.group('start_time')
                end_date = result.group('end_date')
                end_time = result.group('end_time')
                is_closed = False
                if start_time == 'CLOSED':
                    start_datetime = tz.localize(datetime.strptime(f'{start_date}0000', datetime_format))
                    start_datetime = Date.from_datetime(start_datetime)
                    end_datetime = None
                    is_closed = True
                else:
                    start_datetime = tz.localize(datetime.strptime(f'{start_date}{start_time}', datetime_format))
                    end_datetime = tz.localize(datetime.strptime(f'{end_date}{end_time}', datetime_format))
                fx_pair = f"{contract.symbol}{contract.currency}"
                fx_pair_id = trading_class_mapping[fx_pair]
                rows.append([start_datetime, end_datetime, fx_pair, fx_pair_id, is_closed, date])

        self.df = pd.DataFrame(
            rows,
            columns=["start_date", "end_date", "FxPair", "FxPairId", "is_closed", "date"]
        )
        return self.df

    def create_models_with_df(self) -> Sequence[TradingCalendar]:
        return [
            self.model(
                date=row["date"],
                start_date=row["start_date"],
                end_date=row["end_date"],
                is_closed=row['is_closed'],
                pair_id=row["FxPairId"],
                data_cut_id=row["DataCutId"]
            )
            for index, row in self.df.iterrows() if row["FxPairId"] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "start_date",
            "pair_id"
        ]
