import time
from abc import ABC
from datetime import datetime
from typing import List, Dict, Sequence, Optional, Type

import logging

import pandas as pd
from django.db import models
from django.utils import timezone

from main.apps.corpay.services.api.connector.forward import CorPayAPIForwardConnector
from main.apps.corpay.services.api.connector.spot import CorPayAPISpotConnector
from main.apps.corpay.services.api.dataclasses.spot import SpotRateBody
from main.apps.corpay.services.api.exceptions import CorPayAPIException, Forbidden
from main.apps.currency.models.currency import Currency
from main.apps.dataprovider.services.importer.provider_handler.corpay.base import CorPayHandler
from main.apps.marketdata.models import DataCut, CorpayFxSpot

logger = logging.getLogger(__name__)


class CorPayFxSpotHandler(CorPayHandler, ABC):
    model: CorpayFxSpot
    api_forward: CorPayAPIForwardConnector
    api_spot: CorPayAPISpotConnector
    config_path: str = 'dataprovider/importer/corpay/fxspot/company_id'
    trigger_interval = 5 # importer trigger interval

    def __init__(self, data_cut_type: DataCut.CutType, model: Type[models.Model], options: Optional[dict] = {}):
        self.api_forward = CorPayAPIForwardConnector()
        self.api_spot = CorPayAPISpotConnector()
        super().__init__(data_cut_type, model)
        self.options = options

    def get_data_from_api(self) -> Optional[pd.DataFrame]:
        now = datetime.now(tz=timezone.utc)
        date = now.replace(minute=now.minute - (now.minute % self.trigger_interval), second=0, microsecond=0)
        amount = 100000
        rows = []

        if self.skip_import(date_time=now):
            self.df = pd.DataFrame(
                rows,
                columns=self.get_df_columns()
            )
            return self.df

        currencies = Currency.objects.all()

        fxpair_id = self.options.get('fxpair_id')
        pairs = self.populate_fxpairs(fxpair_id=fxpair_id, used_currencies=currencies)

        client_access_code = None

        if len(pairs) > 0:
            company = self.company
            client_access_code = self.get_company_access_code(company=company)

        if client_access_code:

            data_cut = self.get_datacut(fxpair_id=fxpair_id, date=date)

            for pair in pairs:
                base_currency, quote_currency = pair.base_currency.mnemonic, pair.quote_currency.mnemonic

                spot_rate_body_bid = SpotRateBody(
                    paymentCurrency=quote_currency,
                    settlementCurrency=base_currency,
                    amount=amount,
                    lockSide='payment'
                )

                spot_rate_body_ask = SpotRateBody(
                    paymentCurrency=base_currency,
                    settlementCurrency=quote_currency,
                    amount=amount,
                    lockSide='payment'
                )

                try:
                    logger.debug(
                        f"Requesting spot quote for ${amount} {quote_currency}/{base_currency}........")
                    response_spot_bid = self.api_spot.spot_rate(client_code=self.client_code,
                                                                access_code=client_access_code,
                                                                data=spot_rate_body_bid)
                    time.sleep(0.5)
                    logger.debug(
                        f"Requesting spot quote for ${amount} {base_currency}/{quote_currency}........")
                    response_spot_ask = self.api_spot.spot_rate(client_code=self.client_code,
                                                                access_code=client_access_code,
                                                                data=spot_rate_body_ask)
                    time.sleep(0.5)

                    rate_bid = response_spot_bid["rate"]["value"]
                    rate_ask = response_spot_ask["rate"]["value"]

                    rate_type = base_currency + quote_currency

                    # Add check for inverted response rateType compared to current pair.
                    # eg. Response rateType is GBPDKK meanwhile the current pair is DKKGBP,
                    # so invert the rate_bid or rate_ask value,
                    # if the rateType is not equal to current pair
                    if response_spot_bid["rate"]["rateType"] != rate_type:
                        rate_bid = 1/rate_bid
                    if response_spot_ask["rate"]["rateType"] != rate_type:
                        rate_ask = 1/rate_ask

                    rate = (rate_ask + rate_bid) / 2
                    data_cut_id = data_cut.pk
                    pair_id = pair.pk

                    rows.append([
                        date, rate, rate_bid, rate_ask, data_cut_id, pair_id
                    ])
                except Forbidden as e:
                    continue
                except CorPayAPIException as e:
                    logger.error(f"Error fetching spot for {pair}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error fetching spot for {pair}: {e}")
                    continue

        self.df = pd.DataFrame(
            rows,
            columns=self.get_df_columns()
        )
        return self.df
    def redis_create_models_with_df(self) -> List[Dict]:
        """
        Creates a list of dictionaries from the DataFrame, which represent records
        to be inserted into Redis. Each dictionary corresponds to one record.
        """
        return [
            {
                "date": row["date"].isoformat() if pd.notnull(row["date"]) else None,
                "rate": row["rate"],
                "rate_bid": row["rate_bid"],
                "rate_ask": row["rate_ask"],
                "data_cut_id": row["data_cut_id"],
                "pair_id": row["pair_id"]
            }
            for index, row in self.df.iterrows() if row["pair_id"] > 0
        ]

    def create_models_with_df(self) -> Sequence[CorpayFxSpot]:
        return [
            self.model(
                date=row["date"],
                rate=row["rate"],
                rate_bid=row["rate_bid"],
                rate_ask=row["rate_ask"],
                data_cut_id=row["data_cut_id"],
                pair_id=row["pair_id"]
            )
            for index, row in self.df.iterrows() if row["pair_id"] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "data_cut_id",
            "pair_id",
        ]

    def get_df_columns(self) -> List[str]:
        return ["date", "rate", "rate_bid", "rate_ask", "data_cut_id", "pair_id"]
