import datetime
import re

import holidays

from main.apps.corpay.services.api.connector.base import CorPayAPIBaseConnector, logger
from main.apps.corpay.services.api.dataclasses.forwards import RequestForwardQuoteBody, CompleteOrderBody, DrawdownBody
from main.apps.corpay.services.api.exceptions import BadRequest


class CorPayAPIForwardConnector(CorPayAPIBaseConnector):
    def forward_guidelines(self, client_code: int, access_code: str):
        url = f"{self.api_url}/api/{client_code}/0/forwards/getInfo"
        headers = self.get_headers(access_code=access_code)
        response = self.make_request(method='get', url=url, data={}, headers=headers)
        response = self.handle_response(response)

        return response['content']

    def request_forward_quote(self, client_code: int, access_code: str, data: RequestForwardQuoteBody):
        url = f"{self.api_url}/api/{client_code}/0/quotes/forward"
        response = self.post_request(url=url, access_code=access_code, data=data)
        return response['content']


    def request_forward_quote_with_date_adjustment(self, client_code: int, access_code: str, data: RequestForwardQuoteBody):
        should_try_request = True
        while should_try_request:
            try:
                should_try_request = False
                return self.request_forward_quote(client_code=client_code, access_code=access_code, data=data)
            except BadRequest as e:
                for arg in e.args:
                    for error in arg['errors']:
                        if error['key'] == 'WeekendHolidayCheck':
                            logger.error(f"{error['message']} - setting maturity to next valid date")
                            regex = r"The maturity date is not valid. The next valid date is ([0-9\-]+)"
                            matches = re.search(regex, error['message'])
                            if matches:
                                for group_num in range(0, len(matches.groups())):
                                    group_num = group_num + 1
                                    maturity_date = matches.group(group_num)
                                    data.maturityDate = maturity_date
                                    should_try_request = True
                        else:
                            logger.error(f"{error['key']} - {error['message']}")
                            should_try_request = False
            except Exception as e:
                logger.error(f"Unable to get forward quote {e}")

    def book_forward_quote(self, client_code: int, access_code: str, quote_id: str):
        url = f"{self.api_url}/api/{client_code}/0/forwards/{quote_id}"
        response = self.post_request(url=url, access_code=access_code)
        return response['content']

    def complete_order(self, client_code: int, access_code: str, forward_id: int, data: CompleteOrderBody):
        url = f"{self.api_url}/api/{client_code}/0/forwards/{forward_id}/completeOrder"
        response = self.post_request(url=url, access_code=access_code, data=data)
        return response['content']

    def forward(self, client_code: int, access_code: str, forward_id: int):
        url = f"{self.api_url}/api/{client_code}/0/forwards/{forward_id}"
        response = self.get_request(url=url, access_code=access_code)
        return response['content']

    def forwards(self, client_code: int, access_code: str):
        url = f"{self.api_url}/api/{client_code}/0/forwards"
        response = self.get_request(url=url, access_code=access_code)
        return response['content']

    def book_drawdown(self, client_code: int, access_code: str, data: DrawdownBody):
        url = f"{self.api_url}/api/{client_code}/0/book-drawdown"
        response = self.post_request(url=url, access_code=access_code, data=data)
        return response['content']

    @staticmethod
    def nearest_weekday(from_date: datetime, timedelta: int):
        target_date = from_date + datetime.timedelta(days=timedelta)
        us_holidays = holidays.US()
        while target_date.weekday() >= 5 or target_date in us_holidays:  # if target date is a weekend or holiday
            target_date += datetime.timedelta(days=1)  # move to next day
        return target_date
