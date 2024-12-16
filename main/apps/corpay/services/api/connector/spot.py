from main.apps.corpay.services.api.connector.base import CorPayAPIBaseConnector
from main.apps.corpay.services.api.dataclasses.spot import SpotRateBody, InstructDealBody, PurposeOfPaymentParams


class CorPayAPISpotConnector(CorPayAPIBaseConnector):
    def spot_rate(self, client_code: int, access_code: str, data: SpotRateBody):
        url = f"{self.api_url}/api/{client_code}/0/quotes/spot"
        response = self.post_request(url=url, access_code=access_code, data=data)
        return response['content']

    def book_deal(self, client_code: int, access_code: str, quote_id: str):
        url = f"{self.api_url}/api/{client_code}/0/quotes/{quote_id}/book"
        response = self.post_request(url=url, access_code=access_code)
        return response['content']

    def instruct_deal(self, client_code: int, access_code: str, data: InstructDealBody):
        url = f"{self.api_url}/api/{client_code}/0/book-order"
        response = self.post_request(url=url, access_code=access_code, data=data)
        return response['content']

    def lookup_orders(self, client_code: int, access_code: str, order_number: str):
        url = f"{self.api_url}/api/{client_code}/0/orders/{order_number}"
        response = self.get_request(url=url, access_code=access_code)
        return response['content']

    def list_orders(self, client_code: int, access_code: str):
        raise NotImplementedError
        url = f"{self.api_url}/api/{client_code}/0/orders"
        response = self.get_request(url=url, access_code=access_code)
        return response['content']

    def purpose_of_payment(self, client_code: int, access_code: str, data: PurposeOfPaymentParams):
        url = f"{self.api_url}/api/{client_code}/0/paymentPurpose"
        response = self.get_request(url=url, access_code=access_code, data=data)
        return response['content']

