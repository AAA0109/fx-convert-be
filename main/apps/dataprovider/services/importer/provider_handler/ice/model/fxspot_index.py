from datetime import datetime, timedelta
# from multiprocessing.managers import BaseManager
from typing import List, Sequence, Optional, Union
from django.db import models
import pytz
import pandas as pd

from hdlib.DateTime.Date import Date
from main.apps.currency.models import Currency, FxPair
from main.apps.dataprovider.services.importer.provider_handler.ice.model.base import IceModelHandler
from main.apps.marketdata.models import DataCut, FxSpotIntra
from ib_insync import *

from main.apps.marketdata.models import FxSpot, IndexAsset, Index


class IceAssetIndexFromFxSpotModelHandler(IceModelHandler):
    model: Index

    def __init__(self, data_cut_type: DataCut.CutType, model: models.Model):
        super().__init__(data_cut_type, model)
        self.history_back_days: int = 1
        self.history_date_start: Optional[datetime] = None
        self.__utc_tz = pytz.timezone('UTC')
        self.__us_est_tz = pytz.timezone('US/Eastern')
        self.dxy_pairs = self.__get_dxy_pairs()

    def get_data_from_model(self) -> Optional[pd.DataFrame]:
        reference_date = self.history_date_start or datetime.now(
            self.__utc_tz).astimezone(self.__us_est_tz)
        history_date_end = reference_date - \
            timedelta(days=self.history_back_days)

        index_assets = IndexAsset.objects.all()
        eod_datacut = DataCut.objects.filter(cut_type=DataCut.CutType.EOD)
        start_date = Date(history_date_end.year, history_date_end.month,
                          history_date_end.day, 17, 0, 0, tzinfo=self.__us_est_tz)

        rows = []

        for i in range(self.history_back_days):
            end_date = start_date + timedelta(days=1)

            for index_asset in index_assets:
                row = self.__populate_row(
                    index_asset=index_asset, start_date=start_date, end_date=end_date, eod_datacut=eod_datacut)
                if row != None:
                    rows.append(row)

            start_date = end_date

        self.df = pd.DataFrame(
            rows,
            columns=["date", "rate_index", "rate_bid_index",
                     "rate_ask_index", 'data_cut_id', 'index_asset_id']
        ) 
        return self.df

    def before_handle(self) -> pd.DataFrame:
        self.df["_index"] = self.df["date"]
        self.df.set_index("_index", inplace=True)

    def add_data_cut_to_df(self):
        return

    def create_models_with_df(self) -> Sequence[FxSpotIntra]:

        return [
            self.model(
                date=index,
                rate_index=row["rate_index"],
                rate_bid_index=row["rate_bid_index"],
                rate_ask_index=row["rate_ask_index"],
                data_cut_id=row["data_cut_id"],
                index_asset_id=row["index_asset_id"]
            )
            for index, row in self.df.iterrows()
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "index_asset_id"
        ]

    def __populate_row(self, index_asset: IndexAsset, start_date: Date, end_date: Date, eod_datacut: Sequence[DataCut]) -> Optional[List[Union[float, Date, int]]]:
        if index_asset.symbol.lower() == 'dxy':
            fxspot_data = FxSpot.objects.filter(
                date__gte=start_date, date__lt=end_date, data_cut__in=eod_datacut)

            if len(fxspot_data) > 0:
                return self.__populate_dxy_data(index_asset=index_asset, fxspot_data=fxspot_data)

        return None

    #To Do: Change fxspot_data type to BaseManager[FxSpot]. Wrong import for Basemanager.
    def __populate_dxy_data(self, index_asset: IndexAsset, fxspot_data: any) -> Optional[List[Union[float, Date, int]]]:
        dxy_fx_spots: List[FxSpot] = []
        for pair in self.dxy_pairs:
            dxy_fx_spots.append(fxspot_data.filter(pair=pair).first())

        if any(spot is None for spot in dxy_fx_spots) == False:
            rate_index = self.__calculate_dxy(
                [fxspot.rate for fxspot in dxy_fx_spots])
            rate_bid_index = self.__calculate_dxy(
                [fxspot.rate_bid for fxspot in dxy_fx_spots])
            rate_ask_index = self.__calculate_dxy(
                [fxspot.rate_ask for fxspot in dxy_fx_spots])

            return [fxspot_data[0].date, rate_index, rate_bid_index, rate_ask_index, fxspot_data[0].data_cut.id, index_asset.id]

        return None

    def __get_dxy_pairs(self):
        dxy_pairs_str = [
            'EURUSD',
            'USDJPY',
            'GBPUSD',
            'USDCAD',
            'USDSEK',
            'USDCHF'
        ]

        dxy_pairs: List[FxPair] = []
        for pair_str in dxy_pairs_str:
            base_currency = Currency.get_currency(pair_str[0:3])
            quote_currency = Currency.get_currency(pair_str[3:6])
            dxy_pairs.append(FxPair.get_pair_from_currency(base_currency=base_currency, quote_currency=quote_currency))
        return dxy_pairs

    def __calculate_dxy(self, rate_values: List[float]) -> float:
        # DXY = 50.14348112 × EURUSD^-0.576 × USDJPY^0.136 × GBPUSD^-0.119 × USDCAD^0.091 × USDSEK^0.042 × USDCHF^0.036
        return 50.14348112 * pow(rate_values[0], -0.576) * pow(rate_values[1], 0.136) * pow(rate_values[2], -0.119) * pow(rate_values[3], 0.091) * pow(rate_values[4], 0.042) * pow(rate_values[5], 0.036)
