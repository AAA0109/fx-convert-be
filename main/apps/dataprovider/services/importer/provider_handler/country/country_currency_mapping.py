from abc import ABC
import pandas as pd
from typing import Optional, Sequence, List
from django.conf import settings


from main.apps.country.models import Country
from main.apps.currency.models.currency import Currency
from main.apps.dataprovider.services.importer.provider_handler.country.base import CountryJsonFileHandler
from django.core.exceptions import ObjectDoesNotExist

 
class CountryMappingHandler(CountryJsonFileHandler, ABC):
    model: Country

    def get_data_from_url(self) -> Optional[pd.DataFrame]:
        pass

    def before_handle(self) -> pd.DataFrame:
        self.df = pd.read_json(self.file_path)
        return self.df

    def transform_data(self):
        rows = self.model.objects.all().values()
        country_iso_df = pd.DataFrame(rows, columns=['name', 'code'])
        country_iso_df.columns = ['country_name', 'country_iso_alpha3']
        self.df = pd.merge(country_iso_df, self.df[[
                           'country_iso_alpha3', 'country_currency_code']], on='country_iso_alpha3', how='inner')
        for index, row in self.df.iterrows():
            currency_mnemonic = row['country_currency_code']
            try:
                currency_instance = Currency.objects.get(
                    mnemonic=currency_mnemonic)
                self.df.at[index, 'country_currency_code'] = currency_instance
            except ObjectDoesNotExist:
                self.df.at[index, 'country_currency_code'] = None

        self.df = self.df.dropna(subset=['country_currency_code'])

    def create_models_with_df(self) -> Sequence[Country]:
        return [
            self.model(

                name=row['country_name'],
                code=row['country_iso_alpha3'],
                currency_code=row['country_currency_code'],

            )
            for index, row in self.df.iterrows()
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            'code',
            'name',
        ]

    def handle_updated_models(self, updated_models: List):
        return updated_models

    def get_return_models(self) -> bool:
        return True

    def get_update_update_field_names(self) -> Optional[Sequence[str]]:
        return [
            "currency_code"
        ]
