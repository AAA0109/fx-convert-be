import logging
from typing import Optional, Sequence

from main.apps.dataprovider.services.importer.provider_handler.reuters.fx_spot import ReutersFxSpotHandler
from main.apps.marketdata.models.fx.rate import FxSpotRange

logger = logging.getLogger(__name__)


class ReutersFxSpotRangeHandler(ReutersFxSpotHandler):
    model: FxSpotRange
 
    def create_models_with_df(self) -> list:
        return [
            self.model(
                date=index,
                pair_id=row["FxPairId"],
                open_bid=row["Open Bid"],
                open_ask=row["Open Ask"],
                open=row["Open"],
                low_bid=row["Low Bid"],
                low_ask=row["Low Ask"],
                low=row["Low"],
                high_bid=row["Bid High"],
                high_ask=row["Ask High"],
                high=row["High"],
                close=row["Close"],
                data_cut_id=row['DataCutId']
            )
            for index, row in self.df.iterrows() if row['FxPairId'] > 0
        ]

    def get_insert_only_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'pair_id',
            'open_bid',
            'open_ask',
            'open',
            'low_bid',
            'low_ask',
            'low',
            'high_bid',
            'high_ask',
            'high',
            'close'
            'data_cut_id'
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'pair_id'
        ]
