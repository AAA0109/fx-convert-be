from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from main.apps.core.services.http_request import ApiBase


class OpenExchangeRatesError(Exception):
    pass


class OpenExchangeRatesNotFoundError(OpenExchangeRatesError):
    """ Client requested a non-existent resource """
    pass


class OpenExchangeRatesMissingAppIdError(OpenExchangeRatesError):
    """ Client did not provide an App ID """
    pass


class OpenExchangeRatesInvalidAppIdError(OpenExchangeRatesError):
    """ Client provided an invalid App ID """
    pass


class OpenExchangeRatesNotAllowedError(OpenExchangeRatesError):
    """ Client doesn't have permission to access requested route/feature """
    pass


class OpenExchangeRatesAccessRestrictedError(OpenExchangeRatesError):
    """ Access restricted for reason given in 'description' """
    pass


class OpenExchangeRatesAccessRestrictedOverUseError(OpenExchangeRatesError):
    """ Access restricted for repeated over-use """
    pass


class OpenExchangeRatesInvalidBaseError(OpenExchangeRatesError):
    """ Client requested rates for an unsupported base currency """
    pass


# ===================

class OpenExClient(ApiBase):
    API_URL_PREFIX = 'https://openexchangerates.org/api'

    def __init__(self, app_id, retries=2):

        self.app_id = app_id

        # Provides cookie persistence, connection-pooling, and configuration.
        self.session = self.get_session()
        self.headers = {'Authorization': f'Token {app_id}'}

        retry_strategy = Retry(
            total=retries,  # Total number of retries to allow
            status_forcelist=[429, 500, 502, 503, 504],  # A set of HTTP status codes that we want to retry
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
            # Allow retries on these methods
            backoff_factor=1,  # Backoff factor to apply between attempts
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount(self.API_URL_PREFIX, adapter)

    def get(self, *args, **kwargs):

        response = self.session.get(*args, **kwargs)
        content = response.json()

        # If we get an HTTP error code, raise an exception
        if response.status_code != 200:
            print('ERROR:', response.status_code, content)
            return None

        return content

    def get_latest(self, base='USD', symbols=None, show_bid_ask=False, show_alternative=False):
        """ Get latest exchange rate for given base currency """
        params = {'base': base}
        if symbols: params['symbols'] = symbols
        if show_bid_ask: params['show_bid_ask'] = 1
        if show_alternative: params['show_alternative'] = 1
        url = f'{self.API_URL_PREFIX}/latest.json'
        return self.get(url, headers=self.headers, params=params)

# ===================
