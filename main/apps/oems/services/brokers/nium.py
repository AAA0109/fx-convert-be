import logging
import uuid

from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from main.apps.broker.models import Broker
from main.apps.core.services.http_request import ApiBase
from main.apps.nium.services.api.exceptions import *
from main.apps.oems.models.ticket import Ticket
from main.apps.settlement.models.wallet import Wallet

logger = logging.getLogger(__name__)


# ======================

class NiumApi(ApiBase):

    def __init__(self, url_base=settings.NIUM_API_BASE,
                 clientId=settings.NIUM_CLIENT_ID, apiKey=settings.NIUM_API_KEY, retries=1, auto=False):

        self.url_base = url_base
        self.client_id = clientId
        self.api_key = apiKey
        self.session = self.get_session()
        self._broker_model = None

        retry_strategy = Retry(
            total=retries,  # Total number of retries to allow
            status_forcelist=[429, 500, 502, 503, 504],  # A set of HTTP status codes that we want to retry
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
            # Allow retries on these methods
            backoff_factor=1,  # Backoff factor to apply between attempts
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount(self.url_base, adapter)

    @property
    def broker_model(self):
        try:
            self._broker_model = Broker.objects.get(name='Nium')
        except Broker.DoesNotExist:
            logger.error('Unable to initialize Nium API, broker does not exist')
        except Exception as e:
            logger.error(f"Unable to initialize Nium API. System Internal Error")
            logger.exception(e)
        return self._broker_model

    def raise_exception(self, response):
        try:
            msg = response.json()
        except:
            msg = 'internal error'

        if response.status_code == 400:
            raise BadRequest('Bad Request', msg)
        elif response.status_code == 401:
            raise Unauthorized('Unauthorized', msg)
        elif response.status_code == 403:
            raise Forbidden('Forbidden', msg)
        elif response.status_code == 404:
            raise NotFound('Not Found', msg)
        elif response.status_code == 405:
            raise MethodNotAllowed('Method Not Allowed', msg)
        elif response.status_code == 429:
            raise TooManyRequests('Too Many Requests', msg)
        elif response.status_code == 500:
            raise InternalServerError('Internal Server Error', msg)
        elif response.status_code == 503:
            raise ServiceUnavailable('Service Unavailable', msg)
        else:
            raise BadRequest('Bad Request', msg)

    def get_customer_hash_id(self, ticket):
        company = ticket.get_company()
        ret = company.niumsettings.customer_hash_id
        if not ret:
            raise ValueError('no nium customer hash id found')
        return ret

    def get_wallet_hash_id(self, ticket):
        company = ticket.get_company()
        sell_currency = ticket.get_sell_currency()
        # should do type=Wallet.WalletType.VIRTUAL_ACCOUNT and status=Wallet.WalletStatus.ACTIVE
        wallets = Wallet.get_wallets(company, self.broker_model, sell_currency)
        # if multiple wallets, see if there is a match in ticket.settlement_info
        if wallets.count() > 1:
            wallets.filter(wallet_id=ticket.settlement_info.settlement_account_id)
        ret = wallets.first().broker_account_id
        if not ret:
            raise ValueError('no valid wallet_hash_id found for {sell_currency.mnemonic}')
        return ret

    # =============

    def get_conversion_schedule(self, ticket):
        if ticket.tenor == Ticket.Tenors.RTP:
            return 'immediate'
        elif ticket.tenor == Ticket.Tenors.ON:
            return 'end_of_day'
        elif ticket.tenor == Ticket.Tenors.TN:
            return 'next_day'
        elif ticket.tenor == Ticket.Tenors.SPOT:
            return '2_days'
        else:
            raise NotImplementedError

    def get_comment(self, ticket):
        return ticket.payment_memo

    def get_lock_period(self, ticket):
        return '5_mins'  # always lock for 5_minutes

    def get_execution_type(self, ticket):
        return 'manual'

    def get_fx_rate(self, from_ccy: str, to_ccy: str):

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-key': self.api_key,
            'x-request-id': str(uuid.uuid4()),
        }

        url = f'{self.url_base}/v2/exchangeRate?sourceCurrencyCode={from_ccy}&destinationCurrencyCode={to_ccy}'
        response = self.get(url, headers=headers)
        if response.status_code == 200:
            body = response.json()
            return body
        else:
            self.raise_exception(response)

    # =================

    QUOTE_TYPES = ['balance_transfer']
    CONVERSION_SCHEDULES = ['immediate', 'end_of_day', 'next_day', '2_days']
    LOCK_PERIODS = ['5_mins', '15_mins', '1_hour', '4_hours', '8_hours', '24_hours']
    EXEC_TYPES = ['at_conversion_time', 'manual']

    def request_for_quote(self, from_ccy, to_ccy, customer_hash_id, amount=None, lock_side=None,
                          quote_type=QUOTE_TYPES[0],
                          conversion_schedule=CONVERSION_SCHEDULES[0], lock_period=LOCK_PERIODS[0],
                          execution_type=EXEC_TYPES[0], ):

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-key': self.api_key,
            'x-request-id': str(uuid.uuid4()),
        }

        data = {
            'sourceCurrencyCode': from_ccy,
            'destinationCurrencyCode': to_ccy,
            'quoteType': quote_type,
            'conversionSchedule': conversion_schedule,
            'lockPeriod': lock_period,
            'executionType': execution_type,
            'customerHashId': customer_hash_id,
        }

        if amount is not None:
            assert amount > 0.0
            if lock_side is None:
                raise ValueError('must provide lock side with amount')
            fld = 'sourceAmount' if lock_side == from_ccy else 'destinationAmount'
            data[fld] = amount

        url = f'{self.url_base}/v1/client/{self.client_id}/quotes'

        response = self.post(url, headers=headers, json=data)

        if response.status_code == 200:
            body = response.json()
            return body
        else:
            self.raise_exception(response)

        print('ERROR:', response.json())

    def get_quote(self, quote_id):

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-key': self.api_key,
            'x-request-id': str(uuid.uuid4()),
        }

        url = f'{self.url_base}/v1/client/{self.client_id}/quotes/{quote_id}'

        response = self.get(url, headers=headers)
        if response.status_code == 200:
            body = response.json()
            return body
        else:
            self.raise_exception(response)

    def execute_quote(self, quote_id, customer_hash_id, wallet_hash_id, source_amount=None, dest_amount=None,
                      comment=None):

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-key': self.api_key,
            'x-request-id': str(uuid.uuid4()),
        }

        data = {
            'quoteId': quote_id,
            'customerComment': comment,
        }

        if source_amount:
            data['sourceAmount'] = source_amount
        elif dest_amount:
            data['destinationAmount'] = dest_amount
        else:
            raise ValueError('must provide a source or dest amount')

        wallet_hash_id = self.format_wallet_hash_id(wallet_hash_id=wallet_hash_id)

        url = f'{self.url_base}/v1/client/{self.client_id}/customer/{customer_hash_id}/wallet/{wallet_hash_id}/conversions'

        response = self.post(url, headers=headers, json=data)

        if response.status_code == 200:
            body = response.json()
            return body
        else:
            self.raise_exception(response)

    def get_execution(self, conversion_id, customer_hash_id, wallet_hash_id):

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-key': self.api_key,
            'x-request-id': str(uuid.uuid4()),
        }

        wallet_hash_id = self.format_wallet_hash_id(wallet_hash_id=wallet_hash_id)

        url = f'{self.url_base}/v1/client/{self.client_id}/customer/{customer_hash_id}/wallet/{wallet_hash_id}/conversions/{conversion_id}'

        response = self.get(url, headers=headers)
        if response.status_code == 200:
            body = response.json()
            return body
        else:
            self.raise_exception(response)

    def complete_execution(self, conversion_id, customer_hash_id, wallet_hash_id):

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-key': self.api_key,
            'x-request-id': str(uuid.uuid4()),
        }

        wallet_hash_id = self.format_wallet_hash_id(wallet_hash_id=wallet_hash_id)

        url = f'{self.url_base}/v1/client/{self.client_id}/customer/{customer_hash_id}/wallet/{wallet_hash_id}/conversions/{conversion_id}/execute'

        response = self.post(url, headers=headers)
        if response.status_code == 200:
            body = response.json()
            return body
        else:
            self.raise_exception(response)

    def cancel_execution(self, conversion_id, customer_hash_id, wallet_hash_id, comment=None):

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-key': self.api_key,
            'x-request-id': str(uuid.uuid4()),
        }

        wallet_hash_id = self.format_wallet_hash_id(wallet_hash_id=wallet_hash_id)

        url = f'{self.url_base}/v1/client/{self.client_id}/customer/{customer_hash_id}/wallet/{wallet_hash_id}/conversions/{conversion_id}/cancel'

        data = {
            'cancellationComment': comment,
        }

        response = self.post(url, headers=headers, json=data)

        if response.status_code == 200:
            body = response.json()
            return body
        else:
            self.raise_exception(response)

    def format_wallet_hash_id(self, wallet_hash_id: str) -> str:
        try:
            if '_' in wallet_hash_id:
                hash_id_split = wallet_hash_id.split('_')
                return hash_id_split[0]
            return wallet_hash_id
        except:
            return wallet_hash_id


# ======================


if __name__ == "__main__":

    # Setup django
    import django

    django.setup()

    customer_hash_id = '05e8bd7d-0068-408e-933d-d267abad3ac7'

    api = NiumApi()

    from_ccy = 'USD'

    for to_ccy in ('EUR', 'BRL', 'MXN', 'KES', 'INR'):
        # rate = api.get_fx_rate( from_ccy, to_ccy )
        # print( 'RATE:', from_ccy, to_ccy, rate )
        quote = api.request_for_quote(from_ccy, to_ccy, customer_hash_id, amount=1000., lock_side=from_ccy)
        if not quote:
            print("ERROR: skipping", to_ccy)
            continue
        print('RTP QUOTE (5 minutes):', from_ccy, 'to', to_ccy, 'Rate:', quote['exchangeRate'], 'AllInRate:',
              quote['netExchangeRate'], 'FeeInBps:',
              round((quote['clientMarkupRate'] / quote['exchangeRate']) * 10000, 1))
