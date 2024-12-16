import logging
from typing import Optional, Sequence, List
from hdlib.DateTime.Date import Date

from main.apps.dataprovider.services.importer.provider_handler.ice.ir_discount import IceIrDiscountHandler
from main.apps.marketdata.models.ir.discount import OISRate

logger = logging.getLogger(__name__)


class IceIrOisRateHandler(IceIrDiscountHandler):
    model: OISRate
 
    def create_models_with_df(self) -> Sequence[OISRate]:
        return [
            self.model(
                date=row["date"],
                currency_id=row["CurrencyId"],
                tenor=row["tenor"],
                maturity=row["maturity"],
                maturity_days=None,
                curve_id=row["Index"],
                rate=row["Rate"],
                rate_bid=row["BidRate"],
                rate_ask=row["AskRate"],
                fixing_rate=row["FixingRate"],
                spread=row["Spread"],
                spread_index=row["SpreadIndex"],
                data_cut_id=row["DataCutId"]
            )
            for index, row in self.df.iterrows() if row["CurrencyId"] > 0
        ]
    def handle_updated_models(self, updated_models: List):
        """ We need to loop through records after """
        if not updated_models:
            return

        for record in updated_models:
            day_counter = record.curve.make_day_counter()
            maturity_days = day_counter.days_between(Date.from_datetime(record.date),
                                                     Date.from_datetime_date(record.maturity))
            record.maturity_days = maturity_days

        return updated_models

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "currency_id",
            "tenor"
        ]

    def get_update_update_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "currency_id",
            "tenor",
            "maturity",
            "maturity_days",
            "curve",
            "rate",
            "rate_bid",
            "rate_ask",
            "fixing_rate",
            "spread",
            "spread_index",
            "data_cut_id"
        ]
