from abc import ABC
import pandas as pd
from typing import Optional, Sequence


from main.apps.country.models import Country
from main.apps.dataprovider.services.importer.provider_handler.country.base import CountryUrlTxtHandler

 
class CountryISOHandler(CountryUrlTxtHandler, ABC):
    model: Country

    def get_data_from_url(self) -> Optional[pd.DataFrame]:
        self.df = pd.read_csv(self.url, sep=",")
        self.df.columns = ['code','CtryNm']
        return self.df

    def clean_data(self) -> pd.DataFrame:
        self.df.fillna(method="ffill", inplace=True)
        return self.df

    def transform_data(self):
        pass

    def create_models_with_df(self) -> Sequence[Country]:
        return [
            self.model(

                name=row['CtryNm'],
                code=row['code'],

            )
            for index, row in self.df.iterrows()
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            'code',
            'name',
        ]

