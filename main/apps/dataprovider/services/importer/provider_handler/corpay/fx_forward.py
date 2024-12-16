import time
from abc import ABC
from datetime import datetime, timedelta
from typing import List, Sequence, Optional, Type
import re
import logging

import pandas as pd
from django.db import models
from django.utils import timezone

from main.apps.corpay.models.currency import CurrencyDefinition

from main.apps.corpay.services.api.connector.forward import CorPayAPIForwardConnector
from main.apps.corpay.services.api.connector.spot import CorPayAPISpotConnector
from main.apps.corpay.services.api.dataclasses.forwards import RequestForwardQuoteBody
from main.apps.corpay.services.api.dataclasses.spot import SpotRateBody
from main.apps.corpay.services.api.exceptions import BadRequest, CorPayAPIException, Forbidden
from main.apps.dataprovider.services.importer.provider_handler.corpay.base import CorPayHandler
from main.apps.marketdata.models import DataCut, CorpayFxForward

logger = logging.getLogger(__name__)


class CorPayFxForwardHandler(CorPayHandler, ABC):
    model: CorpayFxForward
    api_forward: CorPayAPIForwardConnector
    api_spot: CorPayAPISpotConnector
    config_path: str = 'dataprovider/importer/corpay/fxforward/company_id'
    trigger_interval = 5 # importer trigger interval
 
    def __init__(self, data_cut_type: DataCut.CutType, model: Type[models.Model], options: Optional[dict] = {}):
        self.api_forward = CorPayAPIForwardConnector()
        self.api_spot = CorPayAPISpotConnector()
        super().__init__(data_cut_type, model)
        self.options = options

    def get_data_from_api(self) -> Optional[pd.DataFrame]:
        now = datetime.now(tz=timezone.utc)
        date = now.replace(minute=now.minute - (now.minute % self.trigger_interval), second=0, microsecond=0)
        tenors = {"1W": 7, "3W": 21, "1M": 30, "1Y": 365}
        amounts = [100000]
        date_format = "%Y-%m-%d"
        rows = []

        if self.skip_import(date_time=now):
            self.df = pd.DataFrame(
                rows,
                columns=self.get_df_columns()
            )
            return self.df

        currencies = CurrencyDefinition.get_forward_currencies()

        fxpair_id = self.options.get('fxpair_id')
        pairs = self.populate_fxpairs(fxpair_id=fxpair_id, used_currencies=currencies)

        client_access_code = None

        if len(pairs) > 0:
            company = self.company
            client_access_code = self.get_company_access_code(company=company)

        if client_access_code:
            data_cut = self.get_datacut(fxpair_id=fxpair_id, date=date)

            for tenor in tenors:
                tenor_days = tenors[tenor]
                for amount in amounts:
                    for pair in pairs:
                        base_currency, quote_currency = pair.base_currency.mnemonic, pair.quote_currency.mnemonic
                        maturity_date = self.api_forward.nearest_weekday(now, tenor_days)
                        # Request Forward Quote
                        forward_quote_request_ask = RequestForwardQuoteBody(
                            amount=amount,
                            buyCurrency=base_currency,
                            forwardType='C',
                            lockSide='payment',
                            maturityDate=maturity_date.strftime(date_format),
                            sellCurrency=quote_currency
                        )
                        forward_quote_request_bid = RequestForwardQuoteBody(
                            amount=amount,
                            buyCurrency=quote_currency,
                            forwardType='C',
                            lockSide='payment',
                            maturityDate=maturity_date.strftime(date_format),
                            sellCurrency=base_currency
                        )
                        spot_rate_body_ask = SpotRateBody(
                            paymentCurrency=base_currency,
                            settlementCurrency=quote_currency,
                            amount=amount,
                            lockSide='payment'
                        )
                        spot_rate_body_bid = SpotRateBody(
                            paymentCurrency=quote_currency,
                            settlementCurrency=base_currency,
                            amount=amount,
                            lockSide='payment'
                        )
                        try:
                            logger.debug(
                                f"Requesting forward quote for {tenor_days} days ${amount} {base_currency}/{quote_currency}........")
                            response_forward_ask = self.request_forward_quote(access_code=client_access_code,
                                                                        data=forward_quote_request_ask,
                                                                        now=now,
                                                                        tenor=tenor_days)
                            time.sleep(0.25)
                            logger.debug(
                                f"Requesting forward quote for {tenor_days} days ${amount} {quote_currency}/{base_currency}........")
                            response_forward_bid = self.request_forward_quote(access_code=client_access_code,
                                                                        data=forward_quote_request_bid,
                                                                        now=now,
                                                                        tenor=tenor_days)
                            time.sleep(0.25)
                            logger.debug(
                                f"Requesting spot quote for ${amount} {base_currency}/{quote_currency}........")
                            response_spot_ask = self.api_spot.spot_rate(client_code=self.client_code,
                                                                        access_code=client_access_code,
                                                                        data=spot_rate_body_ask)
                            time.sleep(0.25)
                            logger.debug(
                                f"Requesting spot quote for ${amount} {quote_currency}/{base_currency}........")
                            response_spot_bid = self.api_spot.spot_rate(client_code=self.client_code,
                                                                        access_code=client_access_code,
                                                                        data=spot_rate_body_bid)
                            time.sleep(0.25)
                        except Forbidden as e:
                            continue
                        except CorPayAPIException as e:
                            continue

                        if response_forward_bid != None and response_forward_ask != None:
                            rate_type = base_currency + quote_currency

                            # get spot rate bid and ask
                            rate_spot_bid = response_spot_bid["rate"]["value"]
                            rate_spot_ask = response_spot_ask["rate"]["value"]

                            if response_spot_bid["rate"]["rateType"] != rate_type:
                                rate_spot_bid = 1/rate_spot_bid
                            if response_spot_ask["rate"]["rateType"] != rate_type:
                                rate_spot_ask = 1/rate_spot_ask

                            # calculate spot rate
                            rate_spot = ( rate_spot_bid + rate_spot_ask ) / 2

                            # get forward rate bid and ask
                            rate_forward_bid = response_forward_bid["rate"]["value"]
                            rate_forward_ask = response_forward_ask["rate"]["value"]

                            if response_forward_bid["rate"]["rateType"] != rate_type:
                                rate_forward_bid = 1/rate_forward_bid
                            if response_forward_ask["rate"]["rateType"] != rate_type:
                                rate_forward_ask = 1/rate_forward_ask

                            # calculate forward rate
                            rate_forward = ( rate_forward_bid + rate_forward_ask ) / 2

                            # calculate forward points bid and ask
                            fwd_points_bid = rate_forward_bid - rate_spot_bid
                            fwd_points_ask = rate_forward_ask - rate_spot_ask

                            # calculate forward points
                            fwd_points = rate_forward - rate_spot

                            data_cut_id = data_cut.pk
                            pair_id = pair.pk

                            rows.append([
                                date, tenor, tenor_days, rate_forward, rate_forward_bid, rate_forward_ask, fwd_points,
                                fwd_points_ask, fwd_points_bid, data_cut_id, pair_id
                            ])

        self.df = pd.DataFrame(
            rows,
            columns=self.get_df_columns()
        )
        return self.df

    def create_models_with_df(self) -> Sequence[CorpayFxForward]:
        return [
            self.model(
                date=row["date"],
                tenor=row["tenor"],
                tenor_days=row["tenor_days"],
                rate=row["rate"],
                rate_bid=row["rate_bid"],
                rate_ask=row["rate_ask"],
                fwd_points=row["fwd_points"],
                fwd_points_ask=row["fwd_points_ask"],
                fwd_points_bid=row["fwd_points_bid"],
                data_cut_id=row["data_cut_id"],
                pair_id=row["pair_id"]
            )
            for index, row in self.df.iterrows() if row["pair_id"] > 0
        ]

    def request_forward_quote(self, access_code: str, data: RequestForwardQuoteBody, now: datetime, tenor: int):
        should_try_request = True
        while should_try_request:
            try:
                should_try_request = False
                response_ask = self.api_forward.request_forward_quote(client_code=self.client_code,
                                                                      access_code=access_code,
                                                                      data=data)
                return response_ask
            except BadRequest as e:
                for arg in e.args:
                    for error in arg['errors']:
                        if error['key'] == 'WeekendHolidayCheck':
                            logger.debug(f"{error['message']} - setting maturity to next valid date")
                            regex = r"The maturity date is not valid. The next valid date is ([0-9\-]+)"
                            matches = re.search(regex, error['message'])
                            if matches:
                                for group_num in range(0, len(matches.groups())):
                                    group_num = group_num + 1
                                    maturity_date = matches.group(group_num)
                                    data.maturityDate = maturity_date
                                    should_try_request = True
                        elif error['key'] == 'MaturityDateExceedsValueDateMax':
                                    date = datetime.strptime(data.maturityDate, "%Y-%m-%d")
                                    one_week = timedelta(days=7)
                                    previous_day = date - one_week
                                    data.maturityDate = previous_day.strftime("%Y-%m-%d")
                                    should_try_request = True
                        elif error['key'] == 'INVALID_SELL_CURRENCY':
                            raise e
                        else:
                            logger.error(f"{error['key']} - {error['message']}")
                            should_try_request = False
            except CorPayAPIException as e:
                raise e
            except Exception as e:
                logger.error(f"Unable to get forward quote {e}")

    def get_df_columns(self) -> List[str]:
        return [
            "date", "tenor", "tenor_days", "rate", "rate_bid", "rate_ask", "fwd_points",
            "fwd_points_ask", "fwd_points_bid", "data_cut_id", "pair_id"
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "data_cut_id",
            "pair_id",
            "tenor",
        ]
