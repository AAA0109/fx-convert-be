import gzip
import logging
from io import BytesIO, TextIOWrapper
from typing import Sequence, Optional

import pandas as pd
from django.conf import settings
from storages.backends.gcloud import GoogleCloudStorage

from main.apps.dataprovider.services.importer.provider_handler.ice.base import IceHandler
from main.apps.marketdata.models import DataCut, FxOptionStrategy

logger = logging.getLogger(__name__)
 

class IceOptionStrategyHandler(IceHandler):
    model: FxOptionStrategy

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        self.df["tenor"] = self.splitted_sd_key.iloc[:, 3].str.upper()
        return self.df

    def transform_data(self) -> pd.DataFrame:
        # this we want to convert the df into df that we want
        df_conv = pd.DataFrame(
            columns=['date', 'FxPairId', 'FxPair', 'tenor', "delivery_days", "expiry_days", 'name', 'strategy',
                     'offset', 'bid_value', 'ask_value', 'mid_value'])
        for index, row in self.df.iterrows():
            if row['FxPairId'] < 0:
                continue
            df1 = {
                "date": [index],
                "FxPairId": [row["FxPairId"]],
                "FxPair": [row["FxPair"]],
                "tenor": [row["tenor"]],
                "delivery_days": [row["DeliveryDays"]],
                "expiry_days": [row["ExpiryDays"]],

                "name": ["ATM"],
                "strategy": ["ATM"],
                "offset": ["0"],

                "bid_value": [row["VolBidATM"]],
                "ask_value": [row["VolAskATM"] if 'VolAskATM' in row else row["VolAskATMR"]],
                "mid_value": [row["VolMidATM"]]
            }
            df2 = {
                "date": [index],
                "FxPairId": [row["FxPairId"]],
                "FxPair": [row["FxPair"]],
                "tenor": [row["tenor"]],
                "delivery_days": [row["DeliveryDays"]],
                "expiry_days": [row["ExpiryDays"]],

                "name": ["Bfly25D"],
                "strategy": ["Bfly"],
                "offset": ["25D"],

                "bid_value": [None],
                "ask_value": [None],
                "mid_value": [row["Bfly25D"]]
            }
            df3 = {
                "date": [index],
                "FxPairId": [row["FxPairId"]],
                "FxPair": [row["FxPair"]],
                "tenor": [row["tenor"]],
                "delivery_days": [row["DeliveryDays"]],
                "expiry_days": [row["ExpiryDays"]],

                "name": ["RR10D"],
                "strategy": ["RR"],
                "offset": ["10D"],

                "bid_value": [None],
                "ask_value": [None],
                "mid_value": [row["RR10D"]]

            }
            df4 = {
                "date": [index],
                "FxPairId": [row["FxPairId"]],
                "FxPair": [row["FxPair"]],
                "tenor": [row["tenor"]],
                "delivery_days": [row["DeliveryDays"]],
                "expiry_days": [row["ExpiryDays"]],

                "name": ["Bfly10D"],
                "strategy": ["Bfly"],
                "offset": ["10D"],

                "bid_value": [None],
                "ask_value": [None],
                "mid_value": [row["Bfly10D"]]
            }
            for dfx in [df1, df2, df3, df4]:
                df_conv = pd.concat([df_conv, pd.DataFrame(dfx)], axis=0)

        self.df = df_conv
        self.create_reverse_pairs()
        return self.df

    def create_models_with_df(self) -> Sequence[FxOptionStrategy]:
        grouped_df = self.df.groupby(['DataCutId', 'FxPairId'])

        for (cut_id, fx_pair_id), group in grouped_df:
            try:
                datacut = DataCut.objects.get(id=cut_id)
                filename = f"{datacut.date.strftime('%Y%m%d')}_FxPairId_{fx_pair_id}.csv.gz"

                with BytesIO() as temp_file:
                    with gzip.GzipFile(fileobj=temp_file, mode='w') as gz:
                        with TextIOWrapper(gz, encoding='utf-8') as wrapper:
                            group.to_csv(wrapper, index=False)
                    temp_file.seek(0)

                    obj, created = self.model.objects.update_or_create(
                        data_cut_id=cut_id,
                        pair_id=fx_pair_id,
                        defaults={
                            "date": datacut.date,
                            "storage_type": self.model.DataType.GCS,
                        },
                    )

                    if settings.APP_ENVIRONMENT in ('development', 'staging', "production"):
                        gcs_file_path = f"data_store/option_strategy_by_date_and_pair/{filename}"
                        storage = GoogleCloudStorage()
                        storage.save(gcs_file_path, temp_file)
                        obj.file.name = gcs_file_path
                    else:
                        obj.file.save(filename, temp_file, save=True)

                    obj.save()
                    logger.info(f"Created FxOptionStrategy object {obj} with created={created}")
            except Exception as e:
                logger.error(f"Error processing group (cut_id={cut_id}, fx_pair_id={fx_pair_id}): {e}", exc_info=True)

        return []

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "data_cut_id",
            "pair_id"
        ]

    def calculate_reverse_values(self, df_new: pd.DataFrame, pair: str, inv_pair: str) -> pd.DataFrame:
        list_df = []
        for name in ["Bfly25D", "Bfly10D", "ATM", "RR10D"]:
            filt = (self.df["FxPair"] == pair) & (self.df["name"] == name)
            df_temp = self.df.loc[filt].copy()
            if name in ["RR10D"]:
                for price in ["bid_value", "ask_value", "mid_value"]:
                    df_temp.loc[:, price] = -1 * df_temp.loc[:, price]

            df_temp["FxPair"] = inv_pair
            df_temp["FxPairId"] = self.fx_pair_id_map[inv_pair]
            list_df.append(df_temp)
        df_inv_pair = pd.concat(list_df, axis=0)
        df_new = pd.concat([df_new, df_inv_pair], axis=0)
        return df_new
