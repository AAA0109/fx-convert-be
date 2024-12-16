from datetime import datetime, timedelta
import logging
import numpy as np
from typing import Optional, Sequence
import pandas as pd

from abc import ABC

from pytz import timezone
from main.apps.corpay.api.serializers.choices import DELIVERY_METHODS
from main.apps.corpay.models.currency import Currency
from main.apps.currency.models.deliverytime import DeliveryTime
from main.apps.dataprovider.services.importer.provider_handler.corpay.xlsx.base import CorpayXlsxHandler
 
logger = logging.getLogger(__name__)


class CurrencyDeliveryTimeHandler(CorpayXlsxHandler, ABC):
    model: DeliveryTime
    delivery_methods = dict((x,y) for x, y in DELIVERY_METHODS)

    def add_data_cut_to_df(self):
        pass

    def before_handle(self) -> pd.DataFrame:
        # change column name to lower case and replace " " with "_"
        self.df.columns = self.df.columns.str.strip().str.lower().str.replace(" ", "_")
        # replace empty value with False
        self.df = self.df.replace(np.nan, False)
        return self.df

    def create_models_with_df(self) -> Sequence[DeliveryTime]:
        currency_delivery_times: Sequence[DeliveryTime] = []
        for index, row in self.df.iterrows():
            currency = Currency.get_currency(row['currency'])

            if currency:
                currency_delivery_times.append(self.model(
                    currency_id=currency.pk,
                    country=row['country'],
                    delivery_method=self._get_delivery_method_key(delivery_method_text=row['method']),
                    delivery_sla=self._get_delivery_sla_value(delivery_sla=row['delivery_sla']),
                    deadline=self._deadline_est_to_utc(deadline=row['deadline(est)'])
                ))
            else:
                logger.warning(f"{row['currency']} mnemonic not found")

        return currency_delivery_times

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return ['currency_id']

    def _get_delivery_method_key(self, delivery_method_text: str) -> str:
        if delivery_method_text == "IACH":
            delivery_method_text = "iACH"
        return list(self.delivery_methods.keys())[list(self.delivery_methods.values()).index(delivery_method_text)]

    def _get_delivery_sla_value(self, delivery_sla: str) -> int:
        return int(''.join(filter(str.isdigit, delivery_sla)))

    def _get_country_name(self, country_name: str) -> str:
        return country_name.lower()

    def _deadline_est_to_utc(self, deadline: datetime.time) -> datetime.time:
        date = datetime.now().strftime("%Y-%m-%d")
        time = str(deadline)
        new_date = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone('EST'))
        utc = new_date.astimezone(tz=timezone('UTC'))
        return utc.time()


