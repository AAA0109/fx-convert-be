import pandas as pd
from django.db.models import Q
from django_bulk_load import bulk_upsert_models
from hdlib.AppUtils.log_util import get_logger, logging

from main.apps.currency.models import FxPair
from main.apps.dataprovider.services.backfiller.triangulation_handler.base import BaseTriangulationBackfiller
from main.apps.marketdata.models import FxSpot, FxForward, DataCut

logger = get_logger(level=logging.INFO)


class FxForwardTriangulationBackfiller(BaseTriangulationBackfiller):

    def _create_instances(self, results):
        fx_spot_instances = []
        for group_name, (df, _) in results.items():
            for idx, row in df.iterrows():
                data_cut = DataCut.objects.get(id=row['data_cut_id'])
                fx_spot = FxForward(
                    pair_id=row['pair_id'],
                    date=data_cut.date,
                    data_cut=data_cut,
                    tenor=row['tenor'],

                    rate=row['rate_forward'],
                    rate_bid=row['rate_bid_forward'],
                    rate_ask=row['rate_ask_forward'],

                    fwd_points=row['fwd_points'],
                    fwd_points_bid=row['fwd_points_bid'],
                    fwd_points_ask=row['fwd_points_ask'],
                    depo_base=row['depo_base'],
                    depo_quote=row['depo_quote']
                )
                fx_spot_instances.append(fx_spot)
        return fx_spot_instances

    def _upsert_instances(self, model_instances):
        bulk_upsert_models(
            models=model_instances,
            pk_field_names=['data_cut', 'pair', 'tenor']
        )

    def _triangulate_all_pairs(self):
        triangulate_pairs = FxPair.objects.exclude(
            base_currency__mnemonic=self.home_currency
        ).filter(
            quote_currency__mnemonic=self.triangulate_currency
        )
        date_filter = Q()
        if self.start_date:
            date_filter &= Q(data_cut__cut_time__gte=self.start_date)
        if self.end_date:
            date_filter &= Q(data_cut__cut_time__lte=self.end_date)

        # Retrieve all home_currency/triangulate_currency forward
        home_to_triang_forwards = FxForward.objects.filter(
            date_filter,
            pair__base_currency__mnemonic=self.home_currency,
            pair__quote_currency__mnemonic=self.triangulate_currency
        ).order_by('data_cut__cut_time')
        df_home_to_triang_forwards = pd.DataFrame(list(home_to_triang_forwards.values()))

        home_to_triang_spots = FxSpot.objects.filter(
            date_filter,
            pair__base_currency__mnemonic=self.home_currency,
            pair__quote_currency__mnemonic=self.triangulate_currency
        ).order_by('data_cut__cut_time')
        df_home_to_triang_spots = pd.DataFrame(list(home_to_triang_spots.values()))

        if df_home_to_triang_forwards.empty:
            raise ValueError(f"{self.home_currency}/{self.triangulate_currency} in FxForward has no data")

        if df_home_to_triang_spots.empty:
            raise ValueError(f"{self.home_currency}/{self.triangulate_currency} in FxSpot has no data")

        home_triang_df = pd.merge(
            df_home_to_triang_forwards,
            df_home_to_triang_spots,
            how='inner',
            on=['data_cut_id', 'pair_id']
        )

        home_triang_df.rename(columns=self._new_column_names, inplace=True)

        all_pair_results = {}
        for triangulate_pair in triangulate_pairs:
            # Determine the other currency in the pair
            other_currency = triangulate_pair.base_currency.mnemonic
            pair = FxPair.get_pair(f"{other_currency}/{self.triangulate_currency}")

            other_to_home_forwards = FxForward.objects.filter(
                date_filter,
                pair__base_currency__mnemonic=other_currency,
                pair__quote_currency__mnemonic=self.home_currency
            ).order_by('data_cut__cut_time')
            df_other_to_home_forwards = pd.DataFrame(list(other_to_home_forwards.values()))

            other_to_home_spots = FxSpot.objects.filter(
                date_filter,
                pair__base_currency__mnemonic=other_currency,
                pair__quote_currency__mnemonic=self.home_currency
            ).order_by('data_cut__cut_time')
            df_other_to_home_spots = pd.DataFrame(list(other_to_home_spots.values()))

            if df_other_to_home_forwards.empty:
                logger.warning(f"{other_currency}/{self.home_currency} in FxForward has no data")
                continue

            if df_other_to_home_spots.empty:
                logger.warning(f"{other_currency}/{self.home_currency} in FxSpot has no data")
                continue

            other_home_df = pd.merge(
                df_other_to_home_forwards,
                df_other_to_home_spots,
                how='inner',
                on=['data_cut_id', 'pair_id']
            )

            other_home_df.rename(columns=self._new_column_names, inplace=True)

            for tenor in other_home_df["tenor"].unique():
                ot_df = other_home_df[other_home_df["tenor"] == tenor].copy()
                ot_df.set_index("date_forward", inplace=True)
                ot_df.rename_axis("date", inplace=True)
                ot_df.sort_index(inplace=True)

                ot_df["pair_id"] = pair.id

                merged_df = pd.merge(
                    other_home_df[other_home_df["tenor"] == tenor].copy(),
                    home_triang_df[home_triang_df["tenor"] == tenor].copy(),
                    on='data_cut_id',
                    suffixes=('_oh', '_ht'), how="inner")

                merged_df.set_index("date_forward_oh", inplace=True)
                merged_df.rename_axis("date", inplace=True)
                merged_df.sort_index(inplace=True)

                spread_oh = (merged_df["fwd_points_ask_oh"] - merged_df["fwd_points_bid_oh"]).copy()
                spread_prime_oh = spread_oh * (1 / merged_df["rate_spot_oh"])
                ot_df["rate_spot"] = merged_df["rate_spot_oh"] * merged_df["rate_spot_ht"]

                ot_df["rate_forward"] = merged_df["rate_forward_oh"] * merged_df["rate_forward_ht"]
                ot_df["fwd_points"] = ot_df["rate_forward"] - ot_df["rate_spot"]
                ot_df["fwd_points_ask"] = ot_df["fwd_points"] + (spread_oh / 2)
                ot_df["fwd_points_bid"] = ot_df["fwd_points"] - (spread_oh / 2)

                ot_df["rate_ask_forward"] = ot_df["rate_spot"] + ot_df["fwd_points_ask"]
                ot_df["rate_bid_forward"] = ot_df["rate_spot"] + ot_df["fwd_points_bid"]

                # Depo Rates
                ot_df["depo_base"] = merged_df["depo_base_oh"]
                ot_df["depo_quote"] = merged_df["depo_base_ht"]
                self._validate(ot_df, ot_df["rate_spot"], pair.name)
                all_pair_results[f"{triangulate_pair.name}|{tenor}"] = (ot_df, spread_prime_oh)

        return all_pair_results

    def _calculate_reverse_pairs(self, all_pair_results):
        reverse_pair_spots = {}
        for key, (ot_df, spread_prime_oh) in all_pair_results.items():

            key_split = key.split("|")
            inverse_pair = FxPair.get_inverse_pair(key_split[0])

            # Calculate triang/other pairs
            to_df = ot_df.copy()

            if inverse_pair is None:
                raise ValueError(f"FxPair {inverse_pair.name} is not registered!")

            to_df["pair_id"] = inverse_pair.id
            to_df["rate_spot"] = 1 / ot_df["rate_spot"]
            to_df["rate_forward"] = 1 / ot_df["rate_forward"]

            to_df["fwd_points"] = to_df["rate_forward"] - to_df["rate_spot"]
            to_df["fwd_points_ask"] = to_df["fwd_points"] + (spread_prime_oh / 2)
            to_df["fwd_points_bid"] = to_df["fwd_points"] - (spread_prime_oh / 2)

            to_df["rate_ask_forward"] = to_df["rate_spot"] + to_df["fwd_points_ask"]
            to_df["rate_bid_forward"] = to_df["rate_spot"] + to_df["fwd_points_bid"]

            to_df["depo_base"] = ot_df["depo_quote"]
            to_df["depo_quote"] = ot_df["depo_base"]

            self._validate(to_df, to_df["rate_spot"], inverse_pair.name)
            reverse_pair_spots[f"{inverse_pair.name}|{key_split[1]}"] = (to_df, spread_prime_oh)
        return reverse_pair_spots

    @staticmethod
    def _validate(fx_forward: pd.DataFrame, spot_mid: pd.Series, pair: str):
        if (fx_forward["rate_ask_forward"] < fx_forward["rate_bid_forward"]).any():
            raise ValueError(f"FxPair {pair} has invalid rates! Ask rate is less than Bid rate.")

        if (fx_forward["fwd_points_ask"] < fx_forward["fwd_points_bid"]).any():
            raise ValueError(
                f"FxPair {pair} has invalid forward points! Ask points rate is less than Bid points rate.")

        rate_map = (("rate_forward", "fwd_points"),
                    ("rate_ask_forward", "fwd_points_ask"),
                    ("rate_bid_forward", "fwd_points_bid"))
        for i, j in rate_map:
            if not (fx_forward[i] == spot_mid + fx_forward[j]).any():
                raise ValueError(f"FxPair {pair} has invalid rates! {i} is not equal to spot_mid + {j}")

    @property
    def _new_column_names(self) -> dict:
        return {
            'id_x': 'id_forward',
            'date_x': 'date_forward',

            'rate_x': 'rate_forward',
            'rate_bid_x': 'rate_bid_forward',
            'rate_ask_x': 'rate_ask_forward',

            'id_y': 'id_spot',
            'date_y': 'date_spot',

            'rate_y': 'rate_spot',
            'rate_bid_y': 'rate_bid_spot',
            'rate_ask_y': 'rate_ask_spot'}
