import functools
import logging
import re
from dataclasses import dataclass
from email.message import EmailMessage
from html.parser import HTMLParser
from io import StringIO
from typing import Literal

import requests
from bs4 import BeautifulSoup

from main.apps.core.models import VendorOauth
from main.apps.core.services import GmailService
from main.apps.corpay.models import CorpaySettings, Confirm
from main.apps.corpay.services.corpay import CorPayExecutionServiceFactory, CorPayService


@dataclass
class DealDetailVO:
    """Class for keeping track of an item in inventory."""
    type: Literal['forward', 'spot']
    client_code: str = None
    deal_number: str = None
    order_number: str = None


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


class EmailConfirmService:

    @functools.cache
    def get_service_for_client(self, client_code: str) -> CorPayService:
        csettings = CorpaySettings.objects.get(client_code=client_code)
        return CorPayExecutionServiceFactory().for_company(company=csettings.company)

    @staticmethod
    def get_email_urls(html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        anchors = soup.find_all('a')
        return [str(link.get('href')) for link in anchors if 'corpay.com' in link.get('href')]

    @staticmethod
    def get_deal_detail(html_content) -> DealDetailVO:
        s = MLStripper()
        s.feed(html_content)
        stripped_text = s.get_data()
        with open('/app/temp/temp.txt', 'w') as fh:  # @todo remover
            fh.write(stripped_text)

        if 'Spot Deal Confirmation' in stripped_text:
            item = DealDetailVO(type='spot')
        elif 'Forward Drawdown Confirmation' in stripped_text:
            item = DealDetailVO(type='forward')
        else:
            return None

        search = re.search('Your Account #: ([0-9]*)', stripped_text)
        item.client_code = search.group(1)

        search = re.search('Deal Number:[ \r\n]*([A-Z0-9]*)', stripped_text)
        item.deal_number = search.group(1)

        search = re.search('Order Number:[ \r\n]*([A-Z0-9]*)', stripped_text)
        if search:
            item.order_number = search.group(1)

        return item

    def process_deal_detail(self, detail: DealDetailVO):
        """
        Process deal detail and save it on DB if not exists
        :param detail:
        """
        try:
            corpay_service = self.get_service_for_client(detail.client_code)
            qs = Confirm.objects.filter(
                company=corpay_service.company,
                confirm_type=detail.type,
                deal_number=detail.deal_number,
                order_number=detail.order_number,
            )
            if qs.exists():
                logging.warning(f'\tConfirmation already exist in DB')
                return None

            if detail.type == Confirm.Type.SPOT.value:
                order_kwargs = dict(
                    order_number=detail.deal_number
                )
            elif detail.type == Confirm.Type.FORWARD.value:
                order_kwargs = dict(
                    order_number=detail.order_number
                )
            else:
                raise Exception('Invalid detail type:', detail.type)

            json_response = corpay_service.get_order_details(**order_kwargs)
            Confirm.objects.create(
                confirm_type=detail.type,
                company=corpay_service.company,
                deal_number=detail.deal_number,
                order_number=detail.order_number,
                content=json_response
            )
            logging.info(f"\tOK")
        except CorpaySettings.DoesNotExist as e:
            logging.error(f"CorpaySettings doesn't exist client_code: {detail.client_code}")
        except Exception as e:
            logging.error(f'Error: {e}')

    def process_email(self, msg: EmailMessage):
        logging.info(f"Processing email: {msg.get('Subject')}")
        body = msg.get_body(preferencelist=('plain', 'html'))
        urls = self.get_email_urls(body.get_content())

        if not urls:
            logging.warning("\tNo urls found.")
            return None

        for url in urls:
            # Fetching email's url content
            response = requests.get(url)
            if not response.status_code == 200:
                logging.error(f"\tFetch error: Status:{response.status_code} {response.content}.")
                continue

            html_content = response.content.decode('utf-8')
            detail = self.get_deal_detail(html_content)
            self.process_deal_detail(detail)

    def fetch_emails_oath(self, oauth: VendorOauth):
        logging.info(f"Processing emails from oauth: {oauth}")
        if oauth.vendor == oauth.Vendor.GOOGLE:
            service = GmailService(oauth)
        else:
            raise Exception("Unknown Vendor")

        for msg in service.read_emails(20):
            self.process_email(msg)
