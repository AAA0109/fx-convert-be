from typing import List, Sequence, Optional
import pytz
import pandas as pd

import logging

from hdlib.DateTime.Date import Date

from main.apps.marketdata.models import FxSpotIntra
from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.base import IbkrApiHandler

logger = logging.getLogger(__name__)


class IbkrFxSpotApiHandler(IbkrApiHandler):
    model: FxSpotIntra
    columns: List[str] = ["date", "rate", "rate_bid", "rate_ask", "FxPair", "FxPairId"]

    def get_data_from_api(self) -> Optional[pd.DataFrame]:
        if self.client is None:
            self.df = pd.DataFrame([], columns=self.columns)
            return self.df

        now = Date.now()
        tz = pytz.timezone('UTC')
        date = Date(now.year, now.month, now.day, now.hour, now.minute, now.second)
        date = tz.localize(date)
        contracts = []
        trading_class_mapping = {}
        for fx_pair in self.get_supported_pairs():
            pair = fx_pair.base_currency.mnemonic + fx_pair.quote_currency.mnemonic
            contract = self.api.get_contract(type="forex", symbol=pair)
            contracts.append(contract)
            trading_class_mapping[f"{contract.symbol}{contract.currency}"] = fx_pair.id
        logger.debug(f"Qualifying contracts")
        contracts = self.client.qualifyContracts(*contracts)
        for contract in contracts:
            logger.debug(f"Requesting market data for {contract}")
            self.client.reqMktData(contract, 'BidAsk', True, False)
            self.client.sleep(0.75)
        rows = []
        for contract in contracts:
            ticker = self.client.ticker(contract)
            if not ticker.hasBidAsk():
                logger.error(f"Unable to get bid/ask for {contract}")
                # TODO: Fire event
                continue
            fx_pair = f"{contract.symbol}{contract.currency}"
            fx_pair_id = trading_class_mapping[fx_pair]
            rows.append([date, ticker.marketPrice(), ticker.bid, ticker.ask, fx_pair, fx_pair_id])

        for contract in contracts:
            self.client.cancelMktData(contract)
        self.df = pd.DataFrame(
            rows,
            columns=self.columns
        )
        return self.df

    def before_handle(self) -> pd.DataFrame:
        if "date" in self.df:
            self.df["_index"] = self.df["date"]
            self.df.set_index("_index", inplace=True)

    def add_data_cut_to_df(self):
        return

    def create_models_with_df(self) -> Sequence[FxSpotIntra]:
        return [
            self.model(
                date=index,
                rate=row["rate"],
                rate_bid=row["rate_bid"],
                rate_ask=row["rate_ask"],
                pair_id=row["FxPairId"]
            )
            for index, row in self.df.iterrows() if row["FxPairId"] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "pair_id"
        ]
