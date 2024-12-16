from typing import Dict

import pandas as pd
from django.db.models import Q
from django_bulk_load import bulk_upsert_models
from hdlib.AppUtils.log_util import get_logger, logging

from main.apps.currency.models import FxPair
from main.apps.dataprovider.services.backfiller.triangulation_handler.base import BaseTriangulationBackfiller
from main.apps.marketdata.models import FxSpot, DataCut

logger = get_logger(level=logging.INFO)


class FxSpotTriangulationBackfiller(BaseTriangulationBackfiller):

    def _create_instances(self, results):
        fx_spot_instances = []
        for pair_name, rates_df in results.items():
            for idx, row in rates_df.iterrows():
                data_cut = DataCut.objects.get(id=row['data_cut_id'])
                fx_spot = FxSpot(
                    pair_id=row['pair_id'],
                    date=data_cut.date,
                    data_cut=data_cut,
                    rate=row['rate'],
                    rate_bid=row['rate_bid'],
                    rate_ask=row['rate_ask']
                )
                fx_spot_instances.append(fx_spot)
        return fx_spot_instances

    def _upsert_instances(self, model_instances):
        bulk_upsert_models(
            models=model_instances,
            pk_field_names=['data_cut', 'pair']
        )

    def _triangulate_all_pairs(self) -> Dict[str, pd.DataFrame]:
        triangulate_pairs = FxPair.objects.exclude(
            base_currency__mnemonic=self.home_currency
        ).filter(
            quote_currency__mnemonic=self.triangulate_currency
        )

        date_filter = Q()
        if self.start_date:
            date_filter &= Q(date__gte=self.start_date)
        if self.end_date:
            date_filter &= Q(date__lte=self.end_date)

        # Retrieve all home_currency/triangulate_currency rates
        home_to_triangulate_spots = FxSpot.objects.filter(
            date_filter,
            pair__base_currency__mnemonic=self.home_currency,
            pair__quote_currency__mnemonic=self.triangulate_currency
        ).order_by('data_cut__cut_time')

        df_home_to_triangulate_spots = pd.DataFrame(list(home_to_triangulate_spots.values()))

        all_pair_results = {}
        for triangulate_pair in triangulate_pairs:
            # Determine the other currency in the pair
            other_currency = triangulate_pair.base_currency.mnemonic
            pair = FxPair.get_pair(f"{other_currency}/{self.triangulate_currency}")

            # Get all rates for the other currency against home_currency
            other_to_home_spots = FxSpot.objects.filter(
                date_filter,
                pair__base_currency__mnemonic=other_currency,
                pair__quote_currency__mnemonic=self.home_currency
            ).order_by('data_cut__cut_time')

            if not other_to_home_spots.exists():
                logger.warning(f"{other_currency}/{self.home_currency} in FxSpot has no data")
                continue

            df_other_to_home_spots = pd.DataFrame(list(other_to_home_spots.values()))

            merged_df = pd.merge(df_other_to_home_spots, df_home_to_triangulate_spots, on='data_cut_id',
                                 suffixes=('_other_to_home', '_home_to_triangulate'), how="left")

            merged_df.set_index("date_other_to_home", inplace=True)
            merged_df.rename_axis("date", inplace=True)
            merged_df.rename(columns={"pair_id_other_to_home": "pair_id"}, inplace=True)
            merged_df["pair_id"] = pair.id

            # Perform triangulation
            merged_df['rate'] = merged_df['rate_other_to_home'] * merged_df['rate_home_to_triangulate']
            merged_df['rate_ask'] = merged_df['rate_ask_other_to_home'] * merged_df['rate_ask_home_to_triangulate']
            merged_df['rate_bid'] = merged_df['rate_bid_other_to_home'] * merged_df['rate_bid_home_to_triangulate']

            self._validate(merged_df, pair.name)
            all_pair_results[triangulate_pair.name] = merged_df[
                ['data_cut_id', 'pair_id', 'rate', 'rate_ask', 'rate_bid']]

        return all_pair_results

    def _calculate_reverse_pairs(self, all_pair_results) -> Dict[str, pd.DataFrame]:
        reverse_pair_spots = {}
        for pair, rates in all_pair_results.items():
            inverse_pair = FxPair.get_inverse_pair(pair)
            reverse_rates = rates.copy()
            reverse_rates["pair_id"] = inverse_pair.id
            reverse_rates['rate'] = 1 / rates['rate']
            reverse_rates['rate_ask'] = 1 / rates['rate_bid']
            reverse_rates['rate_bid'] = 1 / rates['rate_ask']
            self._validate(reverse_rates, inverse_pair.name)
            reverse_pair_spots[inverse_pair.name] = reverse_rates
        return reverse_pair_spots

    @staticmethod
    def _validate(fx_spot: pd.DataFrame, pair: str):
        if (fx_spot["rate_ask"] < fx_spot["rate_bid"]).any():
            raise ValueError(f"FxPair {pair} has invalid rates! Ask rate is less than Bid rate.")

        if (fx_spot["rate_ask"] < fx_spot["rate"]).any():
            raise ValueError(f"FxPair {pair} has invalid rates! Ask rate is less than rate.")

        if (fx_spot["rate"] < fx_spot["rate_bid"]).any():
            raise ValueError(f"FxPair {pair} has invalid rates! rate is less than Bid rate.")
