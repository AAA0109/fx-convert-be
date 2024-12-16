from abc import ABC
from typing import Optional, Sequence

import pandas as pd

from main.apps.dataprovider.services.importer.provider_handler.spi.base import SpiHandler
from main.apps.currency.models import StabilityIndex


class SocialProgressIndexHandler(SpiHandler, ABC):
 
    def create_models_with_df(self) -> Sequence[StabilityIndex]:
        return [
            self.model(
                date=row['spiyear'],
                name=self._get_name_with_unit(row),
                parent_index_id=row['parent_index'],
                type='Social Progress Index',
                description=row['description'],
                value=row['value'],
                average_value=row['avg_value'],
                rank=row['rank'],
                currency_id=row['currency_code']
            )
            for index, row in self.df.iterrows()
        ]

    def _get_name_with_unit(self, row) -> str:
        name = row['name']
        unit = row['unit']
        spicountrycode = row['spicountrycode'] if pd.notna(row['spicountrycode']) else row['country']
        
        if unit is not None:
            name += ' ' + unit + ' | ' + spicountrycode
        else:
            name += ' | ' + spicountrycode
        return name

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'name',
            'currency_id',
            'parent_index_id'
        ]
