import pandas as pd


class FxForwardMixin:
    fx_pair_id_map: dict

    def calculate_reverse_values(self, df_new: pd.DataFrame, pair: str, inv_pair: str) -> pd.DataFrame:
        filt = (self.df["FxPair"] == pair)
        df_pair = self.df.loc[filt].copy()
        df_pair["FxPair"] = inv_pair
        df_pair["FxPairId"] = self.fx_pair_id_map[inv_pair]
        df_new = pd.concat([df_new, df_pair], axis=0)
        return df_new
