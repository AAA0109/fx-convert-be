from abc import ABC
import logging
import pandas as pd
from typing import List, Optional, Sequence
import requests
from requests.adapters import HTTPAdapter, Retry
from django.conf import settings

from main.apps.ndl.models import sge
from main.apps.country.models import Country
from main.apps.dataprovider.services.importer.provider_handler.ndl.base import NdlUrlHandler


class SGEHandler(NdlUrlHandler, ABC):

    """
    This handler is responsible for handling and processing NDL SGE data for the SGE model.
    """

    model: sge
    df = None

    def get_data_from_url(self) -> Optional[pd.DataFrame]:
        print("Start importing SGE data...")
        s = requests.Session()
        retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        s.mount('https://', HTTPAdapter(max_retries=retries))

        country_code_dict = self._get_country_code_list() 
        print(country_code_dict)
        df_list = []  

        if country_code_dict:
            for currency_code, country_codes in country_code_dict.items():
                for country in country_codes:
                    for type in self.types_to_fetch:
                        try:
                            response = s.get(f'{self.url}{country}{type}.json?api_key={settings.NSADAQ_DATA_LINK_API_KEY}', verify=False, timeout=2)
                            response.raise_for_status()

                            if response.status_code == 200: 
                                response_content = response.content.decode('utf-8')
                                tempdf = pd.read_json(response_content)
                                tempdf = pd.DataFrame(tempdf["dataset"]["data"], columns=['date', 'value'])
                                tempdf['country'] = country
                                tempdf['value_type'] = type
                                tempdf['currency_code'] = str(currency_code)
                                df_list.append(tempdf)  

                        except requests.exceptions.HTTPError as e:
                            if response.status_code == 404:
                                print(f"URL not found, skip the URL: {response.url}")
                                continue  
                            else:
                                print(f"An error occurred: {str(e)}")
                                raise
            if df_list:
                self.df = pd.concat(df_list, axis=0) 
                self.df = self.df.groupby(['date', 'currency_code', 'value_type']).agg({'value': 'mean', 'country': lambda x: list(x)}).reset_index()
                self.df = self.df.sort_values(by=['value_type', 'date'])

        else:
            logging.info("Country-code list is empty, please import country first")
        return self.df


    def clean_data(self) -> pd.DataFrame:
        self.df.fillna(method="ffill", inplace=True)
        return self.df

    def transform_data(self):
        currency_map = self._get_currency_id_map()
        print(currency_map)
        self.df['currency_code'] = self.df['currency_code'].map(currency_map)

    def create_models_with_df(self) -> Sequence[sge]:
        return [
            self.model(
                date=row['date'],
                value=row['value'],
                country_codes = ",".join(row['country']),
                value_type=row['value_type'],
                currency=row['currency_code'],
            )
            for index, row in self.df.iterrows()
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'value_type',
            'currency'
        ]

    def handle_updated_models(self, updated_models: List):
        return updated_models

    def get_return_models(self) -> bool:
        return True

    def get_update_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'value_type',
            'currency'
        ]

    def get_update_update_field_names(self) -> Optional[Sequence[str]]:
        return [
            'value',
            'country_codes'
        ]
