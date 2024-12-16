import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from itertools import product
from typing import Optional

from croniter import croniter
from django.conf import settings
from requests.exceptions import ConnectionError, RetryError

from main.apps.account.models.company import Company
from main.apps.core.models.config import Config
from main.apps.corpay.services.api.connector.auth import CorPayAPIAuthConnector
from main.apps.corpay.services.api.connector.forward import CorPayAPIForwardConnector
from main.apps.corpay.services.api.connector.spot import CorPayAPISpotConnector
from main.apps.corpay.services.api.dataclasses.forwards import RequestForwardQuoteBody
from main.apps.corpay.services.api.dataclasses.spot import SpotRateBody
from main.apps.corpay.services.api.exceptions import CorPayAPIException
from main.apps.corpay.services.corpay import CorPayService
from main.apps.dataprovider.services.collectors.collector import BaseCollector
from main.apps.dataprovider.services.collectors.quote_tick import QuoteTickFactory, TICK_TYPES, QUOTE_TYPE, QuoteTick
from main.apps.oems.backend.calendar_utils import get_fx_settlement_info
from main.apps.oems.backend.utils import sleep_for

logger = logging.getLogger(__name__)


# ==========================

class CorpayRfqCollector:
    """
    This is an example rfq collector.
    It can be run independently or attached to a runner.
    """

    source = 'CORPAY'
    tenor_days = {"SPOT": 0, "SN": 1, "1W": 7, "3W": 21, "1M": 30, "3M": 90, "6M": 180, "1Y": 365}
    config_path: str = 'dataprovider/importer/corpay/fxforward/company_id'

    def __init__(self, collector_nm, mkts, tenors,
                 collect_fwd_points=True, post_request_sleep=0.25,
                 schedule='* * * * *', writer=None, cache=None, publisher=None, max_workers=1, **kwargs):

        for tenor in tenors:
            if tenor not in self.tenor_days:
                raise ValueError("TENOR NOT HANDLED", tenor)
        self.company = self.get_company_from_config_path()
        self.client_code = self.company.corpaysettings.client_code
        self.auth_api = CorPayAPIAuthConnector()
        self.api_forward = CorPayAPIForwardConnector()
        self.api_spot = CorPayAPISpotConnector()
        self.collector = BaseCollector(collector_nm, self.source, writer=writer, cache=cache, publisher=publisher)
        self.schedule = schedule
        self.iter = croniter(schedule)
        self.next_update = self.iter.get_next()
        self.mkts = mkts
        self.tenors = tenors
        self.factory = QuoteTickFactory(collector=collector_nm, source=self.source,
                                        tick_type=TICK_TYPES.QUOTE, quote_type=QUOTE_TYPE.RFQ,
                                        indicative=False, data_class=QuoteTick)
        self.max_workers = max_workers
        self.collect_fwd_points = collect_fwd_points

        self.post_request_sleep = post_request_sleep

        self.client_access_code = None

    # ================

    def sleep(self):
        if self.post_request_sleep is not None:
            sleep_for(self.post_request_sleep)

    def get_client_access_code(self):
        response = self.auth_api.partner_level_token_login()
        partner_access_code = response['access_code']
        response = self.auth_api.client_level_token_login(
            user_id=self.company.corpaysettings.user_id,
            client_level_signature=self.company.corpaysettings.signature,
            partner_access_code=partner_access_code
        )
        client_access_code = response['access_code']
        return client_access_code

    def get_company_access_code(self, company: Company) -> Optional[str]:
        try:
            corpay_service = CorPayService()
            corpay_service.init_company(company)
            client_access_code = corpay_service.get_client_access_code()
        except Exception as e:
            traceback.print_exc()
            client_access_code = None
            logger.error(f"Credential not exist for company {company.name}")
        return client_access_code

    def get_company_from_config_path(self) -> Company:
        config = Config.get_config(path=self.config_path)
        company_id = config.value
        company = Company.get_company(company=company_id)
        return company

    # ================

    def two_way_wrapper(self, args):
        try:
            return self.two_way_quote(args[0], args[1])
        except:
            traceback.print_exc()

    def two_way_quote(self, instrument: str, tenor: str, amount: int = 100_000):

        # ccy1 = USD
        # ccy2 = JPY

        if self.client_access_code is None:
            company = self.get_company_from_config_path()
            self.client_access_code = self.get_company_access_code(company=company)

        tdy = datetime.utcnow()

        ccy1, ccy2 = instrument[:3], instrument[3:]

        # make sure you are snapping the amount to the same side

        logger.info(f'fetching: {instrument} {tenor}')

        bid_response = ask_response = None

        if tenor == 'SPOT':

            maturity_date = None
            tenor_days = 0

            body_bid = SpotRateBody(
                paymentCurrency=ccy1,
                settlementCurrency=ccy2,
                amount=amount,
                lockSide='payment'
            )

            body_ask = SpotRateBody(
                paymentCurrency=ccy2,
                settlementCurrency=ccy1,
                amount=amount,
                lockSide='settlement'
            )

            ask_time = datetime.utcnow()
            # from ccy1 to ccy2
            try:
                ask_response = self.api_spot.spot_rate(client_code=self.client_code,
                                                       access_code=self.client_access_code,
                                                       data=body_bid)
            except (ConnectionError, RetryError):
                ask_response = None
            except CorPayAPIException as e:
                ask_response = None
            finally:
                self.sleep()

            bid_time = datetime.utcnow()
            # from ccy2 to ccy1
            try:
                bid_response = self.api_spot.spot_rate(client_code=self.client_code,
                                                       access_code=self.client_access_code,
                                                       data=body_ask)
            except (ConnectionError, RetryError):
                bid_response = None
            except CorPayAPIException as e:
                ask_response = None
            finally:
                self.sleep()

        else:

            info = get_fx_settlement_info(instrument, dt=tdy, tenor=tenor)  # expand tenor

            if info:
                maturity_date = info['settle_date']
                tenor_days = info['days']
            else:
                tenor_days = self.tenor_days[tenor]
                maturity_date = self.api_forward.nearest_weekday(tdy, tenor_days).date()

            mdate = maturity_date.isoformat()

            body_ask = RequestForwardQuoteBody(
                amount=amount,
                buyCurrency=ccy1,
                forwardType='C',
                lockSide='payment',
                maturityDate=mdate,
                sellCurrency=ccy2
            )
            body_bid = RequestForwardQuoteBody(
                amount=amount,
                buyCurrency=ccy2,
                forwardType='C',
                lockSide='settlement',
                maturityDate=mdate,
                sellCurrency=ccy1
            )

            try:
                ask_time = datetime.utcnow()
                ask_response = self.api_forward.request_forward_quote(client_code=self.client_code,
                                                                      access_code=self.client_access_code,
                                                                      data=body_ask)
            except CorPayAPIException as e:
                ask_response = None
            except (ConnectionError, RetryError):
                ask_response = None
            finally:
                self.sleep()

            try:
                bid_time = datetime.utcnow()
                bid_response = self.api_forward.request_forward_quote(client_code=self.client_code,
                                                                      access_code=self.client_access_code,
                                                                      data=body_bid)
            except CorPayAPIException as e:
                bid_response = None
            except (ConnectionError, RetryError):
                bid_response = None
            finally:
                self.sleep()

        try:
            bid_rate = bid_response['rate']['value']
            if bid_response["rate"]["rateType"] != instrument:
                bid_rate = 1 / bid_rate
        except TypeError:
            bid_rate = None

        try:
            ask_rate = ask_response['rate']['value']
            if ask_response["rate"]["rateType"] != instrument:
                ask_rate = 1 / ask_rate
        except TypeError:
            ask_rate = None

        if bid_rate is None and ask_rate is None:
            return

        try:
            mid_rate = (ask_rate + bid_rate) / 2.0
        except:
            mid_rate = None

        bid_expiry = bid_time + timedelta(seconds=10)
        ask_expiry = ask_time + timedelta(seconds=10)

        # how to handle the instrument needs to be thought out
        instrument = f'{ccy1}{ccy2}-{tenor}'

        logger.info(f'{bid_time} {instrument} {bid_rate} {ask_rate} {tenor}')

        return dict(
            instrument=instrument,
            bid=bid_rate,
            bid_time=bid_time,
            bid_expiry=bid_expiry,
            bid_size=amount,
            ask=ask_rate,
            ask_time=ask_time,
            ask_expiry=ask_expiry,
            ask_size=amount,
            mid=mid_rate,
            maturity_date=maturity_date,
            tenor_days=tenor_days
        )

    def handle_responses(self, instrument, responses):
        spot = None
        for response in responses:
            if response is None: continue
            self.collector.collect(factory=self.factory, **response)
            if response['instrument'].endswith('-SPOT'):
                spot = response

        if self.collect_fwd_points and spot:
            for response in responses:
                if response is None: continue
                if not response['instrument'].endswith('-SPOT'):
                    response['instrument'] += '-FWDPOINTS'
                    try:
                        response['bid'] = response['bid'] - spot['bid']
                    except TypeError:
                        pass
                    try:
                        response['ask'] = response['ask'] - spot['ask']
                    except TypeError:
                        pass
                    try:
                        response['mid'] = response['mid'] - spot['mid']
                    except TypeError:
                        pass
                    self.collector.collect(factory=self.factory, **response)

    def rfq(self):
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for instrument in self.mkts:
                responses = list(executor.map(self.two_way_wrapper, product([instrument], self.tenors)))
                try:
                    self.handle_responses(instrument, responses)
                except:
                    traceback.print_exc()

    def cycle(self, now, flush=True):
        if now > self.next_update:
            logger.info(f'updating: {now} {self.next_update}')
            self.rfq()
            if flush: self.collector.flush()
            self.next_update = self.iter.get_next()

    def close(self):
        if self.collector:
            self.collector.close()

    def run_forever(self):
        try:
            while True:
                now = time.time()
                self.cycle(now)
                sleep_for(1.0)
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

# ============
