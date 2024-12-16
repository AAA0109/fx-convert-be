import gzip
import logging
from io import BytesIO, TextIOWrapper
from typing import Sequence, Optional

import pandas as pd
from django.conf import settings
from storages.backends.gcloud import GoogleCloudStorage

from main.apps.dataprovider.services.importer.provider_handler.ice.base import IceHandler
from main.apps.marketdata.models import FxOption, DataCut

logger = logging.getLogger(__name__)


class IceOptionHandler(IceHandler):
    model: FxOption

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        self.splitted_sd_key.drop(columns=[0, 1, 2], inplace=True)
        self.splitted_sd_key.columns = ["tenor", "name"]
        self.splitted_sd_key.loc[:, ["tenor", "name"]] = self.splitted_sd_key.loc[:, ["tenor", "name"]].apply(
            lambda x: x.astype(str).str.upper())

        splited_names = self.splitted_sd_key.loc[:, "name"].str.split(r"D", expand=True)
        splited_names.columns = ["delta", "call_put"]

        self.splited_sd_key = pd.concat([self.splitted_sd_key, splited_names], axis=1)
        self.splited_sd_key["delta"] = self.splited_sd_key["delta"].apply(lambda x: 0 if x == "ATM" else x).astype(
            "float64")
        self.splited_sd_key["call_put"] = self.splited_sd_key["call_put"].apply(lambda x: "A" if x == None else x)

        self.df = pd.concat([self.df, self.splited_sd_key], axis=1)
        self.df["ExpiryDate"] = pd.to_datetime(self.df["ExpiryDate"], format="%Y-%m-%d").apply(
            lambda x: x.tz_localize(self.tz))
        self.df["expiry_days"] = (self.df["ExpiryDate"] - self.df["date"]).dt.days
        return self.df

    def transform_data(self) -> pd.DataFrame:
        self.create_reverse_pairs()
        return self.df

    def create_models_with_df(self) -> Sequence[FxOption]:
        grouped_df = self.df.groupby(['DataCutId', 'FxPairId'])

        for (cut_id, fx_pair_id), group in grouped_df:
            try:
                if group.empty:
                    logger.info(
                        f"Skipping group with cut_id={cut_id} and fx_pair_id={fx_pair_id} because it is empty.")
                    continue

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
                        gcs_file_path = f"data_store/option_by_date_and_pair/{filename}"
                        storage = GoogleCloudStorage()
                        storage.save(gcs_file_path, temp_file)
                        obj.file.name = gcs_file_path
                    else:
                        obj.file.save(filename, temp_file, save=True)

                    obj.save()
                    logger.info(f"Created FxOption object {obj} with created={created}")
            except Exception as e:
                logger.error(f"Error processing group (cut_id={cut_id}, fx_pair_id={fx_pair_id}): {e}", exc_info=True)

        return []

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "data_cut_id",
            "pair_id"
        ]

    def calculate_reverse_values(self, df_new: pd.DataFrame, pair: str, inv_pair: str) -> pd.DataFrame:
        filt = (self.df['FxPair'] == pair)
        df_inv_pair = self.df.loc[filt].copy()
        df_inv_pair["call_put"] = df_inv_pair["call_put"].str.replace("C", "temp", regex=True)
        df_inv_pair["call_put"] = df_inv_pair["call_put"].str.replace("P", "C", regex=True)
        df_inv_pair["call_put"] = df_inv_pair["call_put"].str.replace("temp", "P", regex=True)

        df_inv_pair["FxPair"] = inv_pair
        df_inv_pair["FxPairId"] = self.fx_pair_id_map[inv_pair]
        df_new = pd.concat([df_new, df_inv_pair], axis=0)
        return df_new
