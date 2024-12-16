import logging
import warnings
from typing import Optional, Sequence, List

import numpy as np
import pandas as pd

from main.apps.core.models import Config
from main.apps.currency.models import FxPair
from main.apps.dataprovider.mixins.services.importer.provider_handler.fx.forawrd import FxForwardMixin
from main.apps.dataprovider.services.importer.provider_handler.ice.base import IceHandler
from main.apps.marketdata.models import FxForward

logger = logging.getLogger(__name__)


class IceFxForwardHandler(FxForwardMixin, IceHandler):
    model: FxForward
    HOME_CURRENCIES_PATH = "system/fxpair/home_currencies"
    TRIANGULATION_CURRENCIES_PATH = "system/fxpair/triangulation_currencies"
 
    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        self.df["tenor"] = self.splitted_sd_key.loc[:, 3].str.upper()
        return self.df

    def transform_data(self) -> pd.DataFrame:
        self.create_reverse_pairs()
        return self.df

    def create_models_with_df(self) -> Sequence[FxForward]:
        return [
            self.model(
                date=index,
                pair_id=row["FxPairId"],
                tenor=row["tenor"],
                interest_days=row["InterestDays"],
                delivery_days=row["DeliveryDays"],
                expiry_days=row["ExpiryDays"],
                rate=row["FwdRateMid"],
                rate_bid=row["FwdRateBid"],
                rate_ask=row["FwdRateAsk"],
                fwd_points=row["FwdPtsMid"],
                fwd_points_bid=row["FwdPtsBid"],
                fwd_points_ask=row["FwdPtsAsk"],
                depo_base=row["DepoBase"],
                depo_quote=row["DepoTerm"],
                data_cut_id=row["DataCutId"]
            )
            for index, row in self.df.iterrows() if row["FxPairId"] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "pair_id",
            "tenor"
        ]

    def calculate_reverse_values(self, df_new: pd.DataFrame, pair: str, inv_pair: str) -> pd.DataFrame:
        list_df = []
        for tenor in self.df["tenor"].unique():
            filt = (self.df["FxPair"] == pair) & (self.df["tenor"] == tenor)
            df_temp = self.df.loc[filt].copy()
            df_inv_pair = df_temp.copy()
            df_inv_pair["FxPair"] = inv_pair
            df_inv_pair["FxPairId"] = self.fx_pair_id_map[inv_pair]
            # ==========================================================================================
            # Forward Rate
            rate_map = (("FwdRateMid", "FwdRateMid"),
                        ("FwdRateBid", "FwdRateAsk"),
                        ("FwdRateAsk", "FwdRateBid"),
                        ("SpotMid", "SpotMid"))
            for key, value in rate_map:
                df_inv_pair[key] = (1 / df_temp[value]).replace([np.inf, -np.inf], np.nan)

            # Forward Pts
            placeholder = (("FwdPtsMid", "FwdRateMid"),
                           ("FwdPtsBid", "FwdRateBid"),
                           ("FwdPtsAsk", "FwdRateAsk"))
            for p1, p2 in placeholder:
                df_inv_pair[p1] = df_inv_pair[p2] - df_inv_pair["SpotMid"]

            # Depo
            inv_values_map = {
                "DepoBase": "DepoTerm",
                "DepoTerm": "DepoBase",
            }
            for key, val in inv_values_map.items():
                df_inv_pair[val] = df_temp[key].copy()
            # ==========================================================================================
            list_df.append(df_inv_pair)

        df_new = pd.concat([df_new] + list_df, axis=0)
        return df_new

    def before_create_models_with_df(self):
        home_currencies = Config.get_config(path=self.HOME_CURRENCIES_PATH).value
        triangulation_currencies = Config.get_config(path=self.TRIANGULATION_CURRENCIES_PATH).value
        combinations = [(x, y) for x in home_currencies for y in triangulation_currencies]

        merged_df = self.df.copy()
        for home, triang in combinations:
            merged_df = self._create_triangulation_pairs(merged_df, home, triang)
        self.df = merged_df

    # ============================PRIVATE METHODS================================
    def _create_triangulation_pairs(self, merged_df: pd.DataFrame, home: str, triang: str) -> pd.DataFrame:
        self._validate_pairs(merged_df)
        fxpairs = self._get_fx_pairs(merged_df)

        try:
            home_triang_df = self._get_home_triang_df(merged_df, fxpairs, home, triang)
        except:
            logger.warning(f"FxPair {home}/{triang} is not available! Skipping the triangulation pairs.")
            return merged_df

        if home_triang_df.empty:
            return merged_df

        other_home_pairs = self._get_other_home_pairs(fxpairs, home, triang)
        additional_pairs_dfs = self._calculate_additional_pairs(merged_df, other_home_pairs, home_triang_df, triang)

        merged_df = pd.concat([merged_df] + additional_pairs_dfs, axis=0)
        return merged_df

    def _validate_pairs(self, merged_df):
        for idx, row in merged_df.iterrows():
            if row["FxPairId"] >= 0:
                continue
            else:
                raise ValueError(f"Fx Pair related to {row['SDKey']} is not registered!")

    def _get_fx_pairs(self, merged_df) -> dict:
        return {FxPair.get_pair(i).name: FxPair.get_pair(i) for i in merged_df["FxPairId"].unique()}

    def _get_home_triang_df(self, merged_df, fxpairs, home, triang) -> pd.DataFrame:
        home_triang_pair_id = fxpairs[f"{home}/{triang}"].id
        home_triang_df = merged_df[merged_df["FxPairId"] == home_triang_pair_id]
        return home_triang_df

    def _get_other_home_pairs(self, fxpairs, home, triang) -> dict:
        return {name: pair for name, pair in fxpairs.items() if
                name.endswith(f"/{home}") and name != f"{triang}/{home}"}

    def _calculate_additional_pairs(self, merged_df, other_home_pairs, home_triang_df, triang) -> List[pd.DataFrame]:
        additional_pairs_dfs = []
        for pair_name, pair in other_home_pairs.items():
            for tenor in home_triang_df["tenor"].unique():

                filter_ = (merged_df["FxPairId"] == pair.id) & (merged_df["tenor"] == tenor)
                other_home_tenor_df = merged_df[filter_].copy()
                if other_home_tenor_df.empty:
                    continue

                home_triang_tenor_df = home_triang_df[home_triang_df["tenor"] == tenor]
                if home_triang_tenor_df.empty:
                    continue
                other = pair_name.split('/')[0]

                other_triang_tenor_df, spread_prime = self._calculate_other_triang_pair(
                    other_home_tenor_df,
                    home_triang_tenor_df,
                    other,
                    triang)
                additional_pairs_dfs.append(other_triang_tenor_df)

                triang_other_tenor_df = self._calculate_triang_other_pair(
                    other_triang_tenor_df,
                    spread_prime,
                    other,
                    triang)

                additional_pairs_dfs.append(triang_other_tenor_df)
        return additional_pairs_dfs

    def _calculate_other_triang_pair(self, other_home_tenor_df, home_triang_tenor_df, other, triang):
        # Calculate other/triang pairs
        other_triang_tenor_df = other_home_tenor_df.copy()
        fxpair_other_triang = FxPair.get_pair(f"{other}/{triang}")
        if fxpair_other_triang is None:
            raise ValueError(f"FxPair {other}/{triang} is not registered!")

        other_triang_tenor_df["FxPairId"] = fxpair_other_triang.id
        other_triang_tenor_df["FxPair"] = f"{other}/{triang}"

        spread = (other_home_tenor_df["FwdPtsAsk"] - other_home_tenor_df["FwdPtsBid"]).copy()
        spread_prime = spread * (1 / other_home_tenor_df["SpotMid"])
        other_triang_tenor_df["SpotMid"] = other_home_tenor_df["SpotMid"] * home_triang_tenor_df["SpotMid"]
        # Calculate Forward Rates
        other_triang_tenor_df["FwdRateMid"] = other_home_tenor_df["FwdRateMid"] * home_triang_tenor_df["FwdRateMid"]

        # Calculate Forward Points
        other_triang_tenor_df["FwdPtsMid"] = other_triang_tenor_df["FwdRateMid"] - other_triang_tenor_df["SpotMid"]
        other_triang_tenor_df["FwdPtsAsk"] = other_triang_tenor_df["FwdPtsMid"] + (spread / 2)
        other_triang_tenor_df["FwdPtsBid"] = other_triang_tenor_df["FwdPtsMid"] - (spread / 2)

        other_triang_tenor_df["FwdRateAsk"] = other_triang_tenor_df["SpotMid"] + other_triang_tenor_df["FwdPtsAsk"]
        other_triang_tenor_df["FwdRateBid"] = other_triang_tenor_df["SpotMid"] + other_triang_tenor_df["FwdPtsBid"]

        # Depo Rates
        other_triang_tenor_df["DepoBase"] = other_home_tenor_df["DepoBase"]
        other_triang_tenor_df["DepoTerm"] = home_triang_tenor_df["DepoTerm"]

        self._validate(other_triang_tenor_df, other_triang_tenor_df["SpotMid"], f"{other}/{triang}")
        return other_triang_tenor_df, spread_prime

    def _calculate_triang_other_pair(self, other_triang_tenor_df, spread_prime, other, triang):
        # Calculate triang/other pairs
        triang_other_tenor_df = other_triang_tenor_df.copy()
        fxpair_triang_other = FxPair.get_pair(f"{triang}/{other}")
        if fxpair_triang_other is None:
            raise ValueError(f"FxPair {triang}/{other} is not registered!")

        triang_other_tenor_df["FxPairId"] = fxpair_triang_other.id
        triang_other_tenor_df["FxPair"] = f"{triang}{other}"
        triang_other_tenor_df["SpotMid"] = 1 / other_triang_tenor_df["SpotMid"]

        triang_other_tenor_df["FwdRateMid"] = 1 / other_triang_tenor_df["FwdRateMid"]

        triang_other_tenor_df["FwdPtsMid"] = triang_other_tenor_df["FwdRateMid"] - triang_other_tenor_df["SpotMid"]
        triang_other_tenor_df["FwdPtsAsk"] = triang_other_tenor_df["FwdPtsMid"] + (spread_prime / 2)
        triang_other_tenor_df["FwdPtsBid"] = triang_other_tenor_df["FwdPtsMid"] - (spread_prime / 2)

        triang_other_tenor_df["FwdRateAsk"] = triang_other_tenor_df["SpotMid"] + triang_other_tenor_df["FwdPtsAsk"]
        triang_other_tenor_df["FwdRateBid"] = triang_other_tenor_df["SpotMid"] + triang_other_tenor_df["FwdPtsBid"]

        triang_other_tenor_df["DepoBase"] = other_triang_tenor_df["DepoTerm"]
        triang_other_tenor_df["DepoTerm"] = other_triang_tenor_df["DepoBase"]

        self._validate(triang_other_tenor_df, triang_other_tenor_df["SpotMid"], f"{triang}/{other}")
        return triang_other_tenor_df

    @staticmethod
    def _validate(fx_forward: pd.DataFrame, spot_mid: pd.Series, pair: str):
        if (fx_forward["FwdRateAsk"] < fx_forward["FwdRateBid"]).any():
            raise ValueError(f"FxPair {pair} has invalid rates! Ask rate is less than Bid rate.")

        if (fx_forward["FwdPtsAsk"] < fx_forward["FwdPtsBid"]).any():
            raise ValueError(
                f"FxPair {pair} has invalid forward points! Ask points rate is less than Bid points rate.")

        rate_map = (("FwdRateMid", "FwdPtsMid"),
                    ("FwdRateAsk", "FwdPtsAsk"),
                    ("FwdRateBid", "FwdPtsBid"))
        for i, j in rate_map:
            if not (fx_forward[i] == spot_mid + fx_forward[j]).any():
                warnings.warn(f"FxPair {pair} has invalid rates! {i} is not equal to spot_mid + {j}")
