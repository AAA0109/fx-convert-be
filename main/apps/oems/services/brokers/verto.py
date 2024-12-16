from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from main.apps.core.services.http_request import ApiBase


# ===============

class VertoAuth(ApiBase):
    MODE = 'apiKey'

    def __init__(self, url_base=settings.VERTO_API_BASE, clientId=settings.VERTO_CLIENT_ID,
                 apiKey=settings.VERTO_API_KEY, auto=True):

        if not clientId or not apiKey:
            raise ValueError('No verto credentials provided.')

        self.url_base = url_base
        self.clientId = clientId
        self.apiKey = apiKey
        self.login_token = None

        if auto:
            self.login()

    def login(self):
        if self.login_token:
            return self.login_token
        else:
            data = {
                "clientId": self.clientId,
                "apiKey": self.apiKey,
                "mode": self.MODE,
            }
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            url = f'{self.url_base}/users/login'
            response = self.post(url, headers=headers, json=data)
            if response.status_code == 200:
                body = response.json()
                if body['success']:
                    self.login_token = body['token']
                    return self.login_token

    def __call__(self):
        return self.login()


# ===============

class VertoApi(ApiBase):

    def __init__(self, url_base=settings.VERTO_API_BASE,
                 clientId=settings.VERTO_CLIENT_ID, apiKey=settings.VERTO_API_KEY, retries=2, auto=False):

        self.url_base = url_base
        self.session = self.get_session()

        retry_strategy = Retry(
            total=retries,  # Total number of retries to allow
            status_forcelist=[429, 500, 502, 503, 504],  # A set of HTTP status codes that we want to retry
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
            # Allow retries on these methods
            backoff_factor=1,  # Backoff factor to apply between attempts
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount(self.url_base, adapter)

        self.get_token = VertoAuth(url_base=url_base, clientId=clientId, apiKey=apiKey, auto=auto)

    def get_side( self, ticket ):
        if ticket.lock_side_id == ticket.sell_currency_id:
            return 'SELL'
        else:
            return 'BUY'

    def get_fx_rate(self, from_ccy: str, to_ccy: str, auth=True):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if auth:
            token = self.get_token()
            headers['Authorization'] = f'Bearer {token}'

        url = f'{self.url_base}/orders/v2.1/fx?currencyFrom={from_ccy}&currencyTo={to_ccy}'
        response = self.get(url, headers=headers)
        if response.status_code == 200:
            body = response.json()
            if body['success']:
                return body

    def create_fx_trade(self, quote_id, amount, verto_side, user_ref, auth=True):

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        if auth:
            token = self.get_token()
            headers['Authorization'] = f'Bearer {token}'

        data = {
            "vfx_token": quote_id,
            "side": verto_side,
            "amount": amount,
            "clientReference": str(user_ref),
        }

        url = f'{self.url_base}/orders/v2.1/fx'

        response = self.post(url, headers=headers, json=data)
        if response.status_code == 200:
            body = response.json()
            if body['success']:
                return body['order']

    def get_fx_trade(self, verto_order_id, auth=True):

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        if auth:
            token = self.get_token()
            headers['Authorization'] = f'Bearer {token}'

        url = f'{self.url_base}/orders/v2.1/fx/{verto_order_id}'
        response = self.get_session().post(url, headers=headers)
        if response.status_code == 200:
            body = response.json()
            if body['success']:
                return body['order']


# ==============

if __name__ == "__main__":
    # Setup django
    import django

    django.setup()

    verto_api = VertoApi()
    rate = verto_api.get_fx_rate('NGN', 'USD')
