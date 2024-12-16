from urllib.parse import urlparse, parse_qs

from main.apps.corpay.services.api.connector.base import CorPayAPIBaseConnector
from main.apps.corpay.services.api.dataclasses.mass_payment import QuotePaymentsBody, BookPaymentsBody


class CorPayAPIMassPaymentConnector(CorPayAPIBaseConnector):
    def quote_payments(self, client_code: int, access_code: str, data: QuotePaymentsBody):
        url = f"{self.api_url}/api/{client_code}/0/quotes-payment"
        response = self.post_request(url=url, access_code=access_code, data=data)
        for link in response['links']:
            if link['rel'] == 'BOOK_PAYMENT':
                parsed_url = urlparse(link['uri'])
                quote_key = parse_qs(parsed_url.query)['quoteKey'][0]
                session_id = parse_qs(parsed_url.query)['loginSessionId'][0]
                response['content']['quote_id'] = quote_key
                response['content']['session_id'] = session_id

        return response['content']

    def book_payments(self, client_code: int, access_code: str, quote_id: str, session_id: str,
                      data: BookPaymentsBody):
        url = (f"{self.api_url}/api/{client_code}/0/payments/bookPayment?"
               f"quoteKey={quote_id}&"
               f"loginSessionId={session_id}")
        response = self.post_request(url=url, access_code=access_code, data=data)
        return response['content']
