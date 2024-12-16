import numpy as np
from typing import Optional, Sequence
import pandas as pd

from abc import ABC
from main.apps.corpay.models.currency import CurrencyDefinition, Currency
from main.apps.dataprovider.services.importer.provider_handler.corpay.xlsx.base import CorpayXlsxHandler


class CorPayCurrencyCapabilityHandler(CorpayXlsxHandler, ABC):
    model: CurrencyDefinition

    def add_data_cut_to_df(self):
        pass
 
    def before_handle(self) -> pd.DataFrame:
        # change column name to lower case and replace " " with "_"
        self.df.columns = self.df.columns.str.strip().str.lower().str.replace(" ", "_")
        # replace empty value with False
        self.df = self.df.replace(np.nan, False)
        return self.df

    def create_models_with_df(self) -> Sequence[CurrencyDefinition]:
        currency_definitions: Sequence[CurrencyDefinition] = []
        for index, row in self.df.iterrows():
            currency = Currency.get_currency(row['currency'])
            if currency:
                currency_definitions.append(self.model(
                    p10=row['p10'],
                    wallet=row['wallet'],
                    wallet_api=row['wallet'],
                    ndf=row['ndf'],
                    fwd_delivery_buying=row['fwd_delivery_buying'],
                    fwd_delivery_selling=row['fwd_delivery_selling'],
                    outgoing_payments=row['outgoing_payments'],
                    incoming_payments=row['incoming_payments'],
                    currency_id=currency.id,
                ))

        return currency_definitions

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return ['currency_id']
