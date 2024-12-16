import atexit
import logging
from abc import ABC
from datetime import datetime, date, timedelta
from typing import Any, Union, Optional, Dict

import pytz
from django.conf import settings
from django.core.cache import cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from main.apps.account.models import Company
from main.apps.broker.models import Broker, BrokerProviderOption
from main.apps.core.services.http_request import ApiBase
from main.apps.currency.models import Currency
from main.apps.monex.models import MonexCompanySettings
from main.apps.monex.services.api.exceptions import *
from main.apps.settlement.models import BeneficiaryBroker, Wallet
from main.apps.settlement.models.beneficiary import Beneficiary


# ===============

class MonexAPIInterface(ABC):
    ...


class MonexService(MonexAPIInterface):
    ...


# ===============

logger = logging.getLogger(__name__)


class MonexApi(ApiBase):
    singleton = None
    ccy_map = {}
    rev_ccy_map = {}
    country_map = {}
    rev_country_map = {}
    account_type_map = {}
    rev_account_type_map = {}

    SESSION_CACHE_KEY = 'monex_session_id'
    SESSION_TIMEOUT = 600  # 10 minutes

    def __init__(self, url_base=settings.MONEX_API_BASE,
                 clientId=settings.MONEX_CLIENT_ID, apiKey=settings.MONEX_API_KEY,
                 client_type='trusted', retries=1, auto=False):

        self.url_base = url_base
        self.session = self.get_session()

        retry_strategy = Retry(
            total=retries,  # Total number of retries to allow
            # A set of HTTP status codes that we want to retry
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST",
                             "PUT", "DELETE", "OPTIONS", "TRACE"],
            # Allow retries on these methods
            backoff_factor=1,  # Backoff factor to apply between attempts
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount(self.url_base, adapter)

        self.clientId = clientId
        self.apiKey = apiKey
        self.client_type = client_type
        self.session_id = None
        self.customer_id = None
        atexit.register(self._close)

    # ===============================

    @classmethod
    def init(cls):
        if not cls.singleton:
            cls.singleton = cls()
        return cls.singleton

    """
    65.246.46.162
    35.226.94.28
    34.16.56.141
    34.132.183.167
    35.193.185.203
    34.41.146.29
    104.198.39.18
    """

    def login(self, company=None):
        self.session_id = cache.get(self.SESSION_CACHE_KEY)
        if self.session_id:
            if company:
                try:
                    self._update_customer_id_if_needed(company)
                except Exception as e:
                    if 'ErrNotLoggedIn' in str(e):
                        self._perform_login(company)
                        self._update_customer_id_if_needed(company)
                    else:
                        raise
            return self.session_id

        self._perform_login(company)

    def _update_customer_id_if_needed(self, company):
        customer_id = self.get_customer_id(company)
        if self.customer_id is None:
            # no customer id yet, continue with login
            return
        if self.customer_id != customer_id:
            self.change_customer_id(customer_id)

    def _perform_login(self, company):
        data = {
            "publicKey": self.clientId,
            "secretKey": self.apiKey,
        }
        headers = self._get_login_headers()
        url = f'{self.url_base}/login/submitApiClientKeys'
        logger.info(f'{url} :: {headers} :: {data}')
        response = self.post(url, headers=headers, json=data)
        self._handle_login_response(response, company)

    def _get_login_headers(self):
        return {
            'X-API-Client': self.client_type,
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.apiKey}',
        }

    def _handle_login_response(self, response, company):
        if response.status_code == 200:
            data = response.json()
            if 'err' in data:
                self.session_id = False
                raise Exception(str(data))
            self.session_id = True
            cache.set(self.SESSION_CACHE_KEY,
                      self.session_id, self.SESSION_TIMEOUT)
            if company:
                self.customer_id = self.get_customer_id(company)
        else:
            self.session_id = False

    def logout(self):
        self.session_id = cache.get(self.SESSION_CACHE_KEY)
        if not self.session_id:
            return
        headers = {
            'X-API-Client': self.client_type,
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.apiKey}',
        }
        url = f'{self.url_base}/login/logout'
        logger.info(f'{url} :: {headers}')
        response = self.post(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if 'err' in data:
                self.session_id = False
                raise Exception(str(data))
            self.session_id = False

    def change_customer_id(self, customer_id):
        if not self.session_id:
            return
        headers = {
            'X-API-Client': self.client_type,
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.apiKey}',
        }
        url = f'{self.url_base}/login/changeCustomerId'
        logger.info(f'{url} :: {headers} :: {customer_id}')
        response = self.post(url, headers=headers, json={
                             'customerId': customer_id})
        if response.status_code == 200:
            data = response.json()
            if 'err' in data:
                self.customer_id = False
                raise Exception(str(data))
            self.customer_id = customer_id
        else:
            self.customer_id = False
            raise Exception(str(response.json()))

    # =================

    @staticmethod
    def parse_datetime(date_as_epoch):
        return datetime.fromtimestamp(date_as_epoch)

    def get_entity_id(self, company):
        try:
            return company.monexcompanysettings.entity_id
        except:
            raise ValueError(f'no monex settings found for {company.name}')
        # return "14697" for testing

    def get_customer_id(self, company):
        try:
            return company.monexcompanysettings.customer_id
        except:
            raise ValueError(f'no monex settings found for {company.name}')

    # return "0016283" # for testing

    def infer_monex_company(self, entity_id=None, customer_id=None, name=None):

        fld = None
        value = None

        if entity_id:
            fld = 'entity_id'
            value = entity_id
        elif customer_id:
            fld = 'customer_id'
            value = customer_id
        elif name:
            fld = 'company_name'
            value = name
        else:
            logger.error('must provide key to lookup company')

        if fld:
            settings = MonexCompanySettings.objects.filter(**{fld: value})
            if settings:
                return settings.first().company

    # ==================

    def get_headers(self, company, login=True):
        if login:
            self.login(company)
        headers = {
            'X-API-Client': self.client_type,
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.apiKey}',
        }
        if company is not None:
            customer_id = self.get_customer_id(company)
            headers['X-Customer-ID'] = customer_id
        return headers

    def _close(self, *args, **kwargs):
        self.logout()

    def raise_exception(self, response):
        logger.info(
            f"Entering raise_exception: status_code={response.status_code}")
        try:
            msg = response.json()
        except:
            msg = 'internal error'
        msg = "MONEX API ERROR: " + str(msg)
        logger.error(f"Raising exception: {msg}")
        if response.status_code == 400:
            raise BadRequest('Bad Request: ' + msg)
        elif response.status_code == 401:
            raise Unauthorized('Unauthorized: ' + msg)
        elif response.status_code == 403:
            raise Forbidden('Forbidden: ' + msg)
        elif response.status_code == 404:
            raise NotFound('Not Found: ' + msg)
        elif response.status_code == 405:
            raise MethodNotAllowed('Method Not Allowed: ' + msg)
        elif response.status_code == 429:
            raise TooManyRequests('Too Many Requests: ' + msg)
        elif response.status_code == 500:
            raise InternalServerError('Internal Server Error: ' + msg)
        elif response.status_code == 503:
            raise ServiceUnavailable('Service Unavailable: ' + msg)
        else:
            raise BadRequest('Bad Request: ' + msg)

    def request_with_relogin(self, method, url, company=None, **kwargs):
        logger.info(
            f"Entering request_with_relogin: method={method.__name__}, url={url}, company={company}")
        try:
            response = method(url, **kwargs)
            logger.info(
                f"Initial response status code: {response.status_code}")
            if response.status_code != 200:
                logger.warning(
                    f"Non-200 status code received: {response.status_code}")
                self.raise_exception(response)
            try:
                json_response = response.json()
                if 'errType' in json_response and json_response['errType'] == 'ErrNotLoggedIn':
                    raise BadRequest('ErrNotLoggedIn')
            except ValueError:
                # Response is not JSON, continue with normal flow
                pass
            return response
        except BadRequest as e:
            logger.error(
                f"BadRequest caught in request_with_relogin: {str(e)}")
            if 'ErrNotLoggedIn' in str(e) or 'sessionExpired' in str(e):
                logger.info(
                    "Session expired or not logged in. Attempting to re-login.")
                self.session_id = None
                cache.delete(self.SESSION_CACHE_KEY)
                self.login(company)
                logger.info("Re-login completed. Retrying original request.")
                response = method(url, **kwargs)
                logger.info(
                    f"Retry response status code: {response.status_code}")
                if response.status_code != 200:
                    logger.warning(
                        f"Non-200 status code received after retry: {response.status_code}")
                    self.raise_exception(response)
                return response
            else:
                logger.error("BadRequest not related to login. Re-raising.")
                raise

    def handle_response(self, response):
        if response.status_code not in [200, 201]:
            self.raise_exception(response)
        response_json = response.json()
        logger.debug(f"Response: {response_json}")
        if 'err' in response_json:
            raise Exception(
                f"{response_json['errType']}: {response_json['err']}")
        if response.status_code in [200, 201]:
            return response_json

    # =====================================

    def get_monex_currency_id(self, ccy):
        ccy = Currency.get_currency(
            currency=ccy) if isinstance(ccy, str) else ccy
        return self.currency_to_monex_id(ccy)

    # =====================================
    # TODO: these endpoints support post-queries + pagination

    def get_all_forwards(self, company=None, limit=1000000):
        headers = self.get_headers(company)
        url = f'{self.url_base}/reports/forwards/getList'
        payload = {
            'limit': limit,
        }
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data)
        if response.status_code != 200:
            self.raise_exception(response)
        try:
            data = response.json()['data']['rows']
        except:
            self.raise_exception(response)
        return data

    def get_all_spot_orders(self, company=None, limit=10000):
        headers = self.get_headers(company)
        url = f'{self.url_base}/tracker/getList'
        payload = {
            'limit': limit,
        }
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data)
        if response.status_code != 200:
            self.raise_exception(response)
        try:
            data = response.json()['data']['rows']
        except:
            self.raise_exception(response)
        return data

    def get_all_open_orders(self, company=None, limit=1000000):
        headers = self.get_headers(company)
        url = f'{self.url_base}/reports/orders/getList'
        payload = {
            'limit': limit,
            'entity': company.monexcompanysettings.entity_id,
        }
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data)
        if response.status_code != 200:
            self.raise_exception(response)
        try:
            data = response.json()['data']['rows']
        except:
            self.raise_exception(response)
        return data

    def get_holding_accounts(self, company=None, limit=1000000):
        headers = self.get_headers(company)
        payload = {
            'limit': limit
        }
        url = f'{self.url_base}/reports/holdingAccounts/getList'
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=payload)
        response = self.handle_response(response)
        try:
            data = response['data']['rows']
            return data
        except:
            self.raise_exception(response)

    def get_holding_reports(self, company=None):
        headers = self.get_headers(company)
        url = f"{self.url_base}/reports/holding"
        payload = {
            "entityId": company.monexcompanysettings.entity_id,
            "entityName": company.monexcompanysettings.company_name
        }
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=payload)
        response = self.handle_response(response)
        return response['data']

    def get_funding_sources(self, company=None):
        headers = self.get_headers(company)
        url = f"{self.url_base}/entities/getFundingSources"
        payload = {
            "entityId": company.monexcompanysettings.entity_id
        }
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=payload)
        response = self.handle_response(response)
        try:
            data = response['data']['fundingSources']
            return data
        except:
            self.raise_exception(response)

    def get_spot_settlement_info(self, trackerId, company=None):
        headers = self.get_headers(company)
        url = f'{self.url_base}/trackPayment/getSettlement'
        payload = {
            'trackingId': trackerId,
        }
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data)
        if response.status_code != 200:
            self.raise_exception(response)
        try:
            data = response.json()['data']['settlement']
        except:
            self.raise_exception(response)
        return data

    # ======================

    def ensure_ccy_map(self):
        if not MonexApi.ccy_map:
            currencies = self.get_currencies(None)
            for ccy in currencies:
                MonexApi.ccy_map[ccy['id']] = ccy
                MonexApi.rev_ccy_map[ccy['code']] = ccy

    def monex_id_to_currency(self, ccy_id: int) -> Currency:
        self.ensure_ccy_map()
        ccy = self.ccy_map[ccy_id]
        return Currency.get_currency(currency=ccy['code'])

    def currency_to_monex_id(self, currency: Currency):
        self.ensure_ccy_map()
        return self.rev_ccy_map[currency.mnemonic]['id']

    def ensure_country_map(self):
        if not MonexApi.country_map:
            countries = self.get_countries(None)
            for country in countries:
                MonexApi.country_map[country['id']] = country
                MonexApi.rev_country_map[country['code']] = country

    def country_code_to_monex_id(self, country_code: str):
        self.ensure_country_map()
        return self.rev_country_map[country_code]['id']

    def monex_id_to_country_code(self, country_id: int):
        self.ensure_country_map()
        return self.country_map[country_id]['code']

    def ensure_account_type_map(self):
        if not MonexApi.account_type_map:
            account_types = self.get_account_types(None)
            for account_type in account_types:
                MonexApi.account_type_map[account_type['id']] = account_type
                MonexApi.rev_account_type_map[account_type['name']
                                              ] = account_type

    def account_type_to_monex_id(self, account_type: str):
        self.ensure_account_type_map()
        return self.rev_account_type_map[account_type]['id']

    def monex_id_to_account_type(self, account_type_id: int):
        self.ensure_account_type_map()
        return self.account_type_map[account_type_id]['name']

    # ============

    def get_currencies(self, company):
        headers = self.get_headers(company)
        url = f'{self.url_base}/reference/currencies/getList'
        response = self.request_with_relogin(
            self.post, url, company, headers=headers)
        if response.status_code != 200:
            self.raise_exception(response)
        try:
            data = response.json()['data']['rows']
            return data
        except:
            self.raise_exception(response)

    def get_currency_pairs(self, company):
        headers = self.get_headers(company)
        url = f'{self.url_base}/reference/currencies/getPairs'
        response = self.request_with_relogin(
            self.post, url, company, headers=headers)
        if response.status_code != 200:
            self.raise_exception(response)
        try:
            data = response.json()['data']['rows']
            return data
        except:
            self.raise_exception(response)

    def get_countries(self, company):
        headers = self.get_headers(company)
        url = f"{self.url_base}/reference/countries/getList"
        response = self.request_with_relogin(
            self.post, url, company, headers=headers)
        response = self.handle_response(response)
        return response['data']['rows']

    def get_account_types(self, company):
        headers = self.get_headers(company)
        url = f"{self.url_base}/reference/accountTypes/getList"
        response = self.request_with_relogin(
            self.post, url, company, headers=headers)
        response = self.handle_response(response)
        return response['data']['rows']

    # =====================================

    INTERVALS = ('now', 'day', 'week', 'month', 'year')

    def get_historical_rates(self, company, market_name, start_date=None, end_date=None, interval='now', ):

        headers = self.get_headers(company)

        if start_date is None:
            start_date = date.today()

        if end_date is None:
            end_date = date.today() + timedelta(days=1)

        data = {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "symbol": market_name,
            "interval": interval
        }

        url = f'{self.url_base}/rates/getHistory'
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data)
        if response.status_code != 200:
            self.raise_exception(response)
        try:
            data = response.json()['data']['rates']
        except:
            self.raise_exception(response)
        return data

    # =====================================

    FWD_TYPES = ('fixed', 'window')

    def get_forward_rate(self, company, from_ccy: str, to_ccy: str, lock_side: str, amount, value_date,
                         start_date=None, fwd_type='fixed', wid=None, validate_value_date=False):

        headers = self.get_headers(company)

        if not wid:
            url = f'{self.url_base}/forwards/start'
            response = self.request_with_relogin(
                self.get, url, company, headers=headers)

            if response.status_code == 200:
                try:
                    data = response.json()['data']['redirect']
                except:
                    self.raise_exception(response)
                wid = data.split('=')[1]
            else:
                self.raise_exception(response)

        if validate_value_date:
            bizOffset = self.lookup_value_date_offset(
                company, from_ccy, to_ccy, value_date, wid=wid)
            if bizOffset is None or bizOffset == 'FORWARD':
                raise ValueError('bad value date selected')

        if not start_date:
            start_date = date.today()

        if isinstance(value_date, date):
            value_date = datetime.combine(value_date, datetime.min.time())

        if isinstance(start_date, date):
            start_date = datetime.combine(start_date, datetime.min.time())

        new_york_tz = pytz.timezone('America/New_York')

        value_date = value_date.astimezone(new_york_tz)
        start_date = start_date.astimezone(new_york_tz)

        sell_ccy = self.get_monex_currency_id(from_ccy)
        buy_ccy = self.get_monex_currency_id(to_ccy)
        lock_ccy = self.get_monex_currency_id(lock_side)

        data = {
            "valueDate": value_date.isoformat(),
            "startDate": start_date.isoformat(),
            "currencyIHaveId": sell_ccy,
            "currencyToPayId": buy_ccy,
            "amount": {
                "amount": amount,
                "currencyId": lock_ccy,
            },
            "type": fwd_type,
            "wid": wid,
        }

        url = f'{self.url_base}/forwards/setupSubmit'
        logger.info(f'{url} :: {headers} :: {data}')
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data)

        if response.status_code != 200:
            self.raise_exception(response)
        else:
            try:
                data = response.json()['data']
            except:
                self.raise_exception(response)

        url = f'{self.url_base}/forwards/getRates'
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json={'wid': wid})
        if response.status_code != 200:
            self.raise_exception(response)
        else:
            try:
                data = response.json()['data']
                data['workflow'] = 'forward'
                data['wid'] = wid
            except:
                self.raise_exception(response)

        return data

    def execute_forward_rate(self, company, wid):
        headers = self.get_headers(company)
        url = f'{self.url_base}/forwards/quoteSubmit'
        response = self.request_with_relogin(self.post, url, company, headers=headers, json={
                                             'wid': wid, 'termsAccepted': True})
        if response.status_code != 200:
            self.raise_exception(response)
        else:
            try:
                data = response.json()
                if "data" in data and data['data'] is None:
                    data = None
            except:
                self.raise_exception(response)
        return data

    def complete_forward_rate(self, company, wid):
        headers = self.get_headers(company)
        url = f'{self.url_base}/forwards/confirmation'
        response = self.request_with_relogin(
            self.get, url, company, headers=headers, params={'wid': wid})
        if response.status_code != 200:
            self.raise_exception(response)
        else:
            try:
                data = response.json()['data']['page']
            except:
                self.raise_exception(response)
        return data

    def drawdown_forward(self, *args, **kwargs):
        # TODO: the forward needs to be drawdown to a beneficiary when it is available
        raise NotImplementedError

    # =====================================

    def get_payment_value_dates(self, company, from_ccy, to_ccy, wid=None):
        logger.info(
            f"Entering get_payment_value_dates: company={company}, from_ccy={from_ccy}, to_ccy={to_ccy}, wid={wid}")
        headers = self.get_headers(company)
        sell_ccy = self.get_monex_currency_id(from_ccy)
        buy_ccy = self.get_monex_currency_id(to_ccy)

        data = {
            "currencyId": buy_ccy,
            "currencyIHaveId": sell_ccy,
        }

        if wid:
            data['wid'] = wid

        url = f'{self.url_base}/payments/getValueDateInfoSimple'

        try:
            logger.info(
                f"Calling request_with_relogin for get_payment_value_dates: url={url}")
            response = self.request_with_relogin(
                self.post, url, company, headers=headers, json=data)
            logger.info(
                f"Response received from request_with_relogin: status_code={response.status_code}")
            logger.info(f"Response content: {response.content}")
            response_json = response.json()
            logger.info(f"Response JSON: {response_json}")
            return response.json()['data']
        except BadRequest as e:
            logger.error(
                f"BadRequest error in get_payment_value_dates: {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in get_payment_value_dates: {str(e)}")
            raise

    def lookup_value_date_offset(self, company: Company, from_ccy: str, to_ccy: str, value_date: Union[date, datetime],
                                 wid: Optional[str] = None) -> Optional[str]:
        logger.info(
            f"Entering lookup_value_date_offset: company={company}, from_ccy={from_ccy}, to_ccy={to_ccy}, value_date={value_date}, wid={wid}")
        if isinstance(value_date, date):
            value_date = datetime.combine(value_date, datetime.min.time())

        try:
            logger.info("Calling get_payment_value_dates")
            vdates = self.get_payment_value_dates(
                company, from_ccy, to_ccy, wid=wid)
            logger.info(f"Received vdates: {vdates}")
        except BadRequest as e:
            logger.error(
                f"BadRequest error in lookup_value_date_offset: {str(e)}")
            if 'ErrNotLoggedIn' in str(e) or 'sessionExpired' in str(e):
                logger.info(
                    "Session expired or not logged in. Attempting to re-login.")
                self.session_id = None
                cache.delete(self.SESSION_CACHE_KEY)
                self.login(company)
                logger.info(
                    "Re-login completed. Retrying get_payment_value_dates.")
                vdates = self.get_payment_value_dates(
                    company, from_ccy, to_ccy, wid=wid)
            else:
                raise

        if value_date > self.parse_datetime(vdates['valueDateDays'][-1]['timestamp']):
            logger.info(
                "Returning 'FORWARD' as value_date is beyond available dates")
            return 'FORWARD'

        offset_map: Dict[str, Dict[str, Any]] = {
            row['date']: row for row in vdates['valueDateDays']}

        # Convert all keys in offset_map to datetime objects for easier comparison
        date_map = {datetime.strptime(
            k, '%Y-%m-%d'): v for k, v in offset_map.items()}

        # Find the nearest date that's not later than value_date
        nearest_date = min(
            (d for d in date_map.keys() if d >= value_date), default=None)

        if nearest_date:
            logger.info(
                f"Returning bizOffset for nearest date: {nearest_date}")
            return date_map[nearest_date]['bizOffset']
        else:
            logger.warning("No suitable date found for bizOffset")
            return None

    # =================

    def get_quick_rate(self, company, from_ccy: str, to_ccy: str, lock_side: str,
                       amount, spot=False, fwd=False, value_date=None, wid=None, holding=False,
                       start_date=None, fwd_type='fixed', validate_value_date=False):

        if not spot and not value_date:
            raise ValueError('must provide spot or a value_date')

        # step 1 + 2: get payment quote
        headers = self.get_headers(company)

        sell_ccy = self.get_monex_currency_id(from_ccy)
        buy_ccy = self.get_monex_currency_id(to_ccy)
        lock_ccy = self.get_monex_currency_id(lock_side)

        data = {
            "currencyIHaveId": sell_ccy,
            "currencyToPayId": buy_ccy,
            "amount": amount,
            "amountCurrencyId": lock_ccy,
            "placeInHolding": holding,
        }

        if spot:
            data['isQuickvDate'] = True
        elif fwd:
            return self.get_forward_rate(company, from_ccy, to_ccy, lock_side, amount, value_date,
                                         start_date=start_date, fwd_type=fwd_type, wid=wid,
                                         validate_value_date=validate_value_date)
        elif value_date:
            # quick quote uses bizOffset : be greedy
            # payment is only < 14 business days otherwise need to use forward
            if isinstance(value_date, str):
                try:
                    value_date = datetime.strptime(
                        value_date, "%Y-%m-%d").date()
                except ValueError:
                    raise ValueError(
                        f"Invalid date format for value_date: {value_date}. Expected format: YYYY-MM-DD")
            elif isinstance(value_date, datetime):
                value_date = value_date.date()
            elif not isinstance(value_date, date):
                raise TypeError(
                    f"value_date must be a string, datetime, or date object, not {type(value_date)} - {value_date}")

            if (value_date - date.today()).days > 22:
                bizOffset = 'FORWARD'
            else:
                bizOffset = self.lookup_value_date_offset(
                    company, from_ccy, to_ccy, value_date)

            if bizOffset is None:
                raise ValueError
            elif bizOffset == 'FORWARD':
                # use forward workflow
                return self.get_forward_rate(company, from_ccy, to_ccy, lock_side, amount, value_date,
                                             start_date=start_date, fwd_type=fwd_type, wid=wid,
                                             validate_value_date=validate_value_date)
            else:
                data['days'] = bizOffset
        else:
            raise ValueError('should not be possible')

        if wid:
            data['wid'] = wid

        url = f'{self.url_base}/payments/startQuick'
        logger.info(f'{url} :: {headers} :: {data}')
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data)
        try:
            data = response.json()['data']
            data['workflow'] = 'payment'
        except:
            self.raise_exception(response)

        return data

    # ====================

    def execute_payment_rate(self, company, wid, workflow='payment'):
        if workflow == 'forward':
            return self.execute_forward_rate(company, wid)
        elif workflow == 'payment':
            # step 3: execute quoted rate
            data = {'wid': wid}
            headers = self.get_headers(company)
            url = f'{self.url_base}/payments/quoteSubmit'
            logger.info(f'{url} :: {headers} :: {data}')
            response = self.request_with_relogin(
                self.post, url, company, headers=headers, json=data)
            if response.status_code != 200:
                self.raise_exception(response)
            else:
                try:
                    data = response.json()['data']
                except:
                    logger.info(response.json())
                    self.raise_exception(response)

            return data
        else:
            raise NotImplementedError

    def complete_payment_rate(self, company, wid, workflow='payment'):
        if workflow == 'forward':
            return self.complete_forward_rate(company, wid)
        elif workflow == 'payment':
            # step 4: complete trade
            data = {'wid': wid}
            headers = self.get_headers(company)
            url = f'{self.url_base}/payments/completeTrade'
            logger.info(f'{url} :: {headers} :: {data}')
            response = self.request_with_relogin(
                self.post, url, company, headers=headers, json=data)
            if response.status_code != 200:
                self.raise_exception(response)
            else:
                try:
                    data = response.json()['data']
                except:
                    self.raise_exception(response)
            return data
        else:
            raise NotImplementedError

    # ===================

    def settle_payment(self, company, wid, beneficiaries, settlement_info):
        # TODO: this sets up the bene + funding information

        # step 5: change to payment setup mode
        data = {'wid': wid}
        headers = self.get_headers(company)
        url = f'{self.url_base}/payments/setup'
        logger.info(f'{url} :: {headers} :: {data}')
        response = self.request_with_relogin(
            self.get, url, company, headers=headers, params=data)
        if response.status_code != 200:
            self.raise_exception(response)
        else:
            try:
                payment_data = response.json()['data']['page']
            except:
                self.raise_exception(response)

        # Step 6: setup payment info
        # Assume we only have 1 bene for now, will need to update if we want to support multiple benes
        beneficiary_data = beneficiaries[0]
        beneficiary_broker = None
        is_wallet = False
        try:
            beneficiary_broker = BeneficiaryBroker.objects.get(
                beneficiary__beneficiary_id=beneficiary_data['beneficiary_id'],
                broker=Broker.objects.get(
                    broker_provider=BrokerProviderOption.MONEX)
            )
        except BeneficiaryBroker.DoesNotExist:
            logger.error(
                f"Unable to settle payment for company: {company.name} "
                f"using beneficiary_id {beneficiary_data['beneficiary_id']}"
            )
            # check if beneficiary_id is a wallet
            try:
                wallet = Wallet.objects.get(
                    wallet_id=beneficiary_data['beneficiary_id'])
                is_wallet = True
            except Wallet.DoesNotExist:
                logger.error(
                    f"Unable to settle payment for company: {company.name} "
                    f"using beneficiary_id {beneficiary_data['beneficiary_id']} as a wallet"
                )

        if beneficiary_broker is not None:
            bene_id = beneficiary_broker.broker_beneficiary_id
            purposeId = beneficiary_broker.beneficiary.default_purpose
            purpose_detail = beneficiary_broker.beneficiary.default_purpose_description
        else:
            is_wallet = True

        data = {
            "wid": wid,
            "valueDate": payment_data['stepData']['valueDate'],
            "amount": {
                # assume there's only a single rate for now
                "amount": payment_data['stepData']['quotedData']['rates'][0]['amount'],
                "currencyId": payment_data['stepData']['currencyToPayId'],
            },
            "currencyToPayId": payment_data['stepData']['currencyToPayId'],
            "currencyIHaveId": payment_data['stepData']['currencyIHaveId'],
            "reference": None,
            #  placeInolding: True # no bene if holding account trade
        }
        if not is_wallet:
            data['bene'] = {
                "id": bene_id
            }
            data['purposeId'] = purposeId
            data['purposeDetails'] = purpose_detail
        else:
            data['placeInHolding'] = True

        url = f'{self.url_base}/payments/addPayment'
        logger.info(f'{url} :: {headers} :: {data}')
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data)
        if response.status_code != 200:
            self.raise_exception(response)
        else:
            try:
                bene_data = response.json()['data']
            except:
                self.raise_exception(response)

        # Step 7: finalize payment
        data = {'wid': wid}
        url = f'{self.url_base}/payments/setupSubmit'
        logger.info(f'{url} :: {headers} :: {data}')
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data)
        if response.status_code != 200:
            self.raise_exception(response)
        else:
            try:
                final_data = response.json()['data']
            except:
                self.raise_exception(response)

        # Step 8: switch to funding mode
        data = {'wid': wid}
        url = f'{self.url_base}/payments/fund'
        logger.info(f'{url} :: {headers} :: {data}')
        response = self.request_with_relogin(
            self.get, url, company, headers=headers, params=data)
        if response.status_code != 200:
            self.raise_exception(response)
        else:
            try:
                funding_data = response.json()['data']['page']
            except:
                self.raise_exception(response)

        # Step 9: submit funding
        # assume we only have one settlement account id for now, will need to update if we have multiple
        try:
            wallet = Wallet.objects.get(
                wallet_id=settlement_info[0]['settlement_account_id'])
        except Wallet.DoesNotExist:
            ...
        # default to Wire
        funding_method = 1
        if len(funding_data['incomingBenes']) > 0:
            funding_method = 21

        # check if funding need payee
        need_payee = None
        if 'fundingMethods' in funding_data and '1' in funding_data['fundingMethods']:
            matched_methods = list(filter(lambda fund_method: fund_method['id'] == funding_method,
                                          funding_data['fundingMethods']['1']))
            if len(matched_methods) > 0:
                need_payee = matched_methods[0]['needPayee']

        # force need payee status if no matched funding method found
        if need_payee is None:
            need_payee = True if funding_method == 21 else False

        data = {
            "blocks": [
                {
                    "ccyId": funding_data['stepData']['quotedData']['totals'][0]['ccy'],
                    "methods": [
                        {
                            "id": funding_method,
                            "amount": funding_data['stepData']['quotedData']['totals'][0]['cost'],
                        }
                    ]
                }
            ],
            "wid": wid,
        }

        # set payeeId if payee required
        if need_payee:
            payee_id = funding_data['defaultFundingBeneId']
            # Use the first incoming bene if defaultFundingBeneId = 0
            if payee_id == 0 and len(funding_data['incomingBenes']) > 0:
                payee_id = funding_data['incomingBenes'][0]['id']

            if payee_id != 0:
                data['blocks'][0]['methods'][0]['payeeId'] = payee_id

        url = f'{self.url_base}/payments/fundSubmit'
        logger.info(f'{url} :: {headers} :: {data}')
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data)
        if response.status_code != 200:
            self.raise_exception(response)
        else:
            try:
                post_fund_data = response.json()['data']
            except:
                self.raise_exception(response)

        # Step 10: confirmation
        data = {'wid': wid}
        url = f'{self.url_base}/payments/confirmation'
        logger.info(f'{url} :: {headers} :: {data}')
        response = self.request_with_relogin(
            self.get, url, company, headers=headers, params=data)
        if response.status_code != 200:
            self.raise_exception(response)
        else:
            try:
                confirmation_data = response.json()['data']['page']
            except:
                self.raise_exception(response)

        return confirmation_data
    # =========================================
