import logging
from typing import Optional, Sequence

from main.apps.dataprovider.services.importer.provider_handler.ice.fx_spot import IceFxSpotHandler
from main.apps.marketdata.models.fx.rate import FxSpotRange

logger = logging.getLogger(__name__)


class IceFxSpotRangeHandler(IceFxSpotHandler):
    model: FxSpotRange
 
    def create_models_with_df(self) -> Sequence[FxSpotRange]:
        return [
            self.model(
                date=index,
                pair_id=row["FxPairId"],
                open=None,
                open_bid=None,
                open_ask=None,
                low=row["Low"],
                low_bid=None,
                low_ask=None,
                high=row["High"],
                high_bid=None,
                high_ask=None,
                close=row["Mid"],
                close_bid=None,
                close_ask=None,
                data_cut_id=row["DataCutId"]
            )
            for index, row in self.df.iterrows() if row["FxPairId"] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "pair_id"
        ]
